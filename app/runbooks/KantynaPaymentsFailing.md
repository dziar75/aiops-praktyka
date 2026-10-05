# KantynaPaymentsFailing

**Severity:** warning
**Condition:** more than 10% of payment requests end with `status="failed"` (`payments_requests_total`) over 5 minutes.

## Symptoms

- Orders stay unpaid / users get "payment failed".
- `orders-api` logs show errors calling `PAYMENTS_URL` (`http://kantyna-payments:8080/pay`).
- `payments` returns 502 to `orders-api`.

## Impact

Orders cannot be completed. Users may retry and create duplicate orders.

## Diagnosis

1. Failure ratio and outcomes:

   ```promql
   sum by (status) (rate(payments_requests_total{namespace="kantyna"}[5m]))
   sum(rate(payments_requests_total{namespace="kantyna", status="failed"}[5m])) / sum(rate(payments_requests_total{namespace="kantyna"}[5m]))
   histogram_quantile(0.95, sum by (le) (rate(payments_duration_seconds_bucket{namespace="kantyna"}[5m])))
   ```

   Note: `status="error"` is client-side validation (HTTP 400); `status="failed"` is a gateway failure (HTTP 502).

2. Pods and version:

   ```bash
   kubectl -n kantyna get pods -l app.kubernetes.io/name=payments
   kubectl -n kantyna logs -l app.kubernetes.io/name=payments --since=15m --tail=100
   ```

   ```promql
   payments_build_info{namespace="kantyna"}
   ```

3. Logs:

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="payments"} | json | outcome="failed"
   sum by (pod) (count_over_time({namespace="kantyna", app_kubernetes_io_name="payments"} | json | outcome="failed" [5m]))
   ```

4. Runtime settings in effect (payments section):

   ```bash
   kubectl -n kantyna get configmap kantyna-flags -o jsonpath='{.data.flags\.json}' | jq .payments
   ```

5. Traces: `{ resource.service.name = "payments" && status = error }`.

## Remediation

| Action | Risk | Command |
|---|---|---|
| Restore payments settings to previous values | Safe | edit `flags.payments` in values, `helm upgrade kantyna deploy/helm/kantyna -n kantyna --reuse-values -f <values>` |
| Restart payments | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-payments` |
| Scale payments | Safe | `kubectl -n kantyna scale deploy/kantyna-payments --replicas=3` |
| Roll back release | Caution | `helm rollback kantyna <REV> -n kantyna` |

Do not replay failed payments manually; reconciliation is done by the payments owner.

## Escalation

- Failure ratio > 50% or > 15 min: page the payments owner.
- External provider outage: inform canteen staff to accept orders without prepayment.
