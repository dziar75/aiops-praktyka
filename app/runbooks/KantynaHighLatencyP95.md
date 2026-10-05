# KantynaHighLatencyP95

**Severity:** warning
**Condition:** p95 of `http_request_duration_seconds` above 1s for 10 minutes.

## Symptoms

- Menu and order pages load slowly; web clients may time out.
- Grafana latency panel shows p95 > 1s; p50 may still look normal (tail latency).

## Impact

Degraded user experience; at higher values requests time out and turn into 5xx errors.

## Diagnosis

1. Which service / endpoint is slow?

   ```promql
   histogram_quantile(0.95, sum by (job, le) (rate(http_request_duration_seconds_bucket{namespace="kantyna"}[5m])))
   histogram_quantile(0.95, sum by (handler, le) (rate(http_request_duration_seconds_bucket{namespace="kantyna", job=~".*orders-api.*"}[5m])))
   ```

2. Is it a dependency? Compare with payments latency:

   ```promql
   histogram_quantile(0.95, sum by (le) (rate(payments_duration_seconds_bucket{namespace="kantyna"}[5m])))
   ```

3. Resource saturation (CPU throttling, memory pressure):

   ```promql
   sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="kantyna", container="orders-api"}[5m]))
   sum by (pod) (rate(container_cpu_cfs_throttled_periods_total{namespace="kantyna", container="orders-api"}[5m]))
     / sum by (pod) (rate(container_cpu_cfs_periods_total{namespace="kantyna", container="orders-api"}[5m]))
   ```

   ```bash
   kubectl -n kantyna top pods
   kubectl -n kantyna describe hpa kantyna-orders-api   # if HPA is enabled
   ```

4. Slow database queries:

   ```bash
   kubectl -n kantyna exec -it sts/kantyna-postgres -- psql -U kantyna -d kantyna -c \
     "select pid, now()-query_start as age, state, left(query,80) from pg_stat_activity where state <> 'idle' order by age desc limit 10;"
   ```

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="orders-api"} | json | duration_ms > 1000
   ```

5. Traces (Tempo): `{ resource.service.name = "orders-api" && duration > 1s }` - check whether time is spent in the DB span, the payments call or the handler itself.

6. Recent changes: `helm -n kantyna history kantyna`, current `kantyna-flags` content.

## Remediation

| Action | Risk | Command |
|---|---|---|
| Scale out (CPU-bound) | Safe | `kubectl -n kantyna scale deploy/kantyna-orders-api --replicas=4` |
| Restart pods (leaked resources, hot loop) | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-orders-api` |
| Revert recent settings change | Safe | restore previous `flags:` values via `helm upgrade ... --reuse-values` |
| Cancel a runaway DB query | Caution | `select pg_cancel_backend(<pid>);` |
| Roll back release | Caution | `helm rollback kantyna <REV> -n kantyna` |

## Escalation

- p95 > 3s or causing errors: treat as [KantynaHighErrorRate](KantynaHighErrorRate.md) and page the orders-api owner.
- Payments latency is the driver: contact the payments owner / payment provider status page.
