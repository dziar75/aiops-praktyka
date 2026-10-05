# KantynaHighErrorRate

**Severity:** warning
**Condition:** more than 5% of HTTP requests return 5xx for 5 minutes (`http_requests_total{status=~"5.."}` / `http_requests_total`).

## Symptoms

- Users see "something went wrong" when browsing the menu or placing an order.
- Grafana: 5xx ratio panel above 5% for `orders-api` (and/or `payments`).
- Increased ERROR logs in Loki for the affected service.

## Impact

Part of lunch orders fail. If it persists over the ordering window (10:00-12:00) people miss lunch orders.

## Diagnosis

1. Which service and which endpoints?

   ```promql
   sum by (job) (rate(http_requests_total{namespace="kantyna", status=~"5.."}[5m]))
     / sum by (job) (rate(http_requests_total{namespace="kantyna"}[5m]))

   topk(10, sum by (job, handler, method, status) (rate(http_requests_total{namespace="kantyna", status=~"5.."}[5m])))
   ```

2. Did it start with a deploy or a settings change?

   ```bash
   helm -n kantyna history kantyna
   kubectl -n kantyna rollout history deploy/kantyna-orders-api
   kubectl -n kantyna get configmap kantyna-flags -o jsonpath='{.data.flags\.json}'
   kubectl -n kantyna get pods -l app.kubernetes.io/name=orders-api -L app.kubernetes.io/version -o wide
   ```

3. Logs (Loki):

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="orders-api"} | json | level="ERROR"
   sum by (logger) (count_over_time({namespace="kantyna", app_kubernetes_io_name="orders-api"} | json | level="ERROR" [5m]))
   ```

4. Downstream dependencies: check payments and the database.

   ```promql
   sum by (status) (rate(payments_requests_total{namespace="kantyna"}[5m]))
   max by (pod) (db_pool_connections_in_use{namespace="kantyna"}) / max by (pod) (db_pool_size{namespace="kantyna"})
   ```

   ```bash
   kubectl -n kantyna logs deploy/kantyna-payments --since=15m | tail -50
   kubectl -n kantyna exec sts/kantyna-postgres -- pg_isready -h 127.0.0.1
   ```

5. Traces (Tempo, Grafana Explore): `{ resource.service.name = "orders-api" && status = error }` - open a sample trace to see which span fails.

## Remediation

| Action | Risk | Command |
|---|---|---|
| Restart pods (clears transient state) | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-orders-api` |
| Scale out if errors correlate with load | Safe | `kubectl -n kantyna scale deploy/kantyna-orders-api --replicas=4` (or raise HPA `minReplicas`) |
| Revert a recent settings change | Safe | restore previous `flags:` values and `helm upgrade kantyna deploy/helm/kantyna -n kantyna --reuse-values -f <values>` |
| Roll back a bad release | Caution | `helm rollback kantyna <REV> -n kantyna` (pick `<REV>` from `helm history`) |

If the cause is in `payments` or the database, follow [KantynaPaymentsFailing](KantynaPaymentsFailing.md) or [KantynaDBPoolExhausted](KantynaDBPoolExhausted.md).

## Escalation

- Not resolved within 30 min or error ratio > 25%: page the Kantyna backend owner (orders-api team).
- Database errors (connection refused, disk full): escalate to the platform/DB on-call.
