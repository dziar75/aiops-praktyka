# KantynaPodOOMKilled

**Severity:** critical
**Condition:** a container's last termination reason is `OOMKilled` and it restarted within the last 30 minutes.

## Symptoms

- `kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`.
- Memory usage graph shows a saw-tooth pattern (grows until the limit, then drops after restart).
- Short bursts of 5xx / dropped connections when a replica dies.

## Impact

In-flight requests on the killed replica fail. Repeated OOMs lead to CrashLoopBackOff and capacity loss.

## Diagnosis

1. Which container:

   ```promql
   kube_pod_container_status_last_terminated_reason{namespace="kantyna", reason="OOMKilled"} == 1
   ```

   ```bash
   kubectl -n kantyna get pods
   kubectl -n kantyna describe pod <pod> | grep -A5 "Last State"
   ```

2. Memory trend vs. limit - steady growth over time suggests a leak, a sudden spike suggests a heavy request:

   ```promql
   sum by (pod) (container_memory_working_set_bytes{namespace="kantyna", container="orders-api"})
   max by (pod) (kube_pod_container_resource_limits{namespace="kantyna", container="orders-api", resource="memory"})
   deriv(container_memory_working_set_bytes{namespace="kantyna", container="orders-api"}[30m])  # bytes/s growth
   ```

3. What was happening before the kill:

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="orders-api"} | json | level=~"WARNING|ERROR"
   ```

   ```bash
   kubectl -n kantyna logs <pod> --previous --tail=200
   ```

4. Recent changes: new release (`helm history`), changed settings (`kantyna-flags`), traffic increase
   (`sum(rate(http_requests_total{namespace="kantyna"}[5m]))`).

## Remediation

| Action | Risk | Command |
|---|---|---|
| Restart to reset memory (buys time for a leak) | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-orders-api` |
| Add replicas to spread load | Safe | `kubectl -n kantyna scale deploy/kantyna-orders-api --replicas=4` |
| Revert recent settings change | Safe | restore previous `flags:` values via `helm upgrade ... --reuse-values` |
| Raise memory limit temporarily | Caution | `helm upgrade kantyna deploy/helm/kantyna -n kantyna --reuse-values --set ordersApi.resources.limits.memory=768Mi` |
| Roll back release | Caution | `helm rollback kantyna <REV> -n kantyna` |

Raising the limit hides a leak - always open a follow-up ticket with the memory graph attached.

## Escalation

- OOM repeats within 1h after restart: page the service owner (likely memory leak).
- Node-level memory pressure (`kubectl describe node`, evictions): escalate to platform on-call.
