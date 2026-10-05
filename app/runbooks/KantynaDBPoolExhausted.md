# KantynaDBPoolExhausted

**Severity:** critical
**Condition:** `db_pool_connections_in_use / db_pool_size` > 0.9 on an `orders-api` pod for 5 minutes.

## Symptoms

- Requests wait for a DB connection: latency rises, then timeouts/5xx (`QueuePool limit ... timed out`).
- `/readyz` may fail and pods drop out of the Service endpoints.

## Impact

Menu and order endpoints become slow or unavailable. Often precedes [KantynaHighErrorRate](KantynaHighErrorRate.md).

## Diagnosis

1. Pool usage per pod - one pod vs. all pods:

   ```promql
   max by (pod) (db_pool_connections_in_use{namespace="kantyna"}) / max by (pod) (db_pool_size{namespace="kantyna"})
   max by (pod) (db_pool_connections_in_use{namespace="kantyna"})
   ```

   Usage that only grows and never returns to baseline, even with low traffic, points to connections not being released.
   Usage that follows traffic points to slow queries or under-sized pool.

2. Database side:

   ```bash
   kubectl -n kantyna exec -it sts/kantyna-postgres -- psql -U kantyna -d kantyna -c \
     "select state, count(*), max(now()-state_change) as oldest from pg_stat_activity where datname='kantyna' group by state;"
   kubectl -n kantyna exec -it sts/kantyna-postgres -- psql -U kantyna -d kantyna -c \
     "select pid, client_addr, state, now()-query_start as age, left(query,80) from pg_stat_activity where datname='kantyna' order by age desc nulls last limit 15;"
   ```

   Many `idle in transaction` sessions = connections leaked by the application.

3. Logs:

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="orders-api"} |= "pool" | json | level=~"WARNING|ERROR"
   ```

4. Recent changes: `helm -n kantyna history kantyna`, `kantyna-flags` content (orders-api section), traffic level.

## Remediation

| Action | Risk | Command |
|---|---|---|
| Restart orders-api (releases all pool connections) | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-orders-api` |
| Delete only the affected pod | Safe | `kubectl -n kantyna delete pod <pod>` |
| Revert recent settings change | Safe | restore previous `flags.orders-api` values via `helm upgrade ... --reuse-values` |
| Terminate leaked idle-in-transaction sessions | Caution | `select pg_terminate_backend(pid) from pg_stat_activity where datname='kantyna' and state='idle in transaction' and now()-state_change > interval '5 minutes';` |
| Roll back release | Caution | `helm rollback kantyna <REV> -n kantyna` |

Do not scale orders-api out to fix this - every new replica opens its own pool and can exhaust `max_connections` on postgres.

## Escalation

- Recurs within hours after restart: page the orders-api owner (connection leak).
- Postgres `max_connections` reached or postgres unhealthy: escalate to platform/DB on-call.
