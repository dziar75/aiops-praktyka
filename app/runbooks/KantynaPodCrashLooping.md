# KantynaPodCrashLooping

**Severity:** critical
**Condition:** a container in namespace `kantyna` restarted more than 3 times in 15 minutes (`kube_pod_container_status_restarts_total`).

## Symptoms

- Pod in `CrashLoopBackOff` or with a rising RESTARTS counter.
- Reduced capacity; when all replicas are affected the service is down.

## Impact

Depends on the component: `orders-api`/`web` - users affected directly; `worker` - orders not processed (backlog); `postgres` - full outage.

## Diagnosis

1. Which pod and why:

   ```bash
   kubectl -n kantyna get pods -o wide
   kubectl -n kantyna describe pod <pod>          # Last State, Reason, Exit Code, Events
   kubectl -n kantyna logs <pod> --previous --tail=200
   kubectl -n kantyna get events --field-selector involvedObject.name=<pod> --sort-by=.lastTimestamp
   ```

   Typical reasons: `OOMKilled` (see [KantynaPodOOMKilled](KantynaPodOOMKilled.md)), exit code 1 (startup error, bad config),
   `Liveness probe failed` (app hangs or is too slow to respond).

2. Restarts trend:

   ```promql
   increase(kube_pod_container_status_restarts_total{namespace="kantyna"}[15m]) > 0
   kube_pod_container_status_last_terminated_reason{namespace="kantyna"} == 1
   ```

3. Logs right before the crash (Loki keeps logs of the previous container):

   ```logql
   {namespace="kantyna", pod="<pod>"} | json | level=~"ERROR|CRITICAL"
   {namespace="kantyna", app_kubernetes_io_name="worker"} |= "Traceback"
   ```

4. Config / dependencies: was there a recent release or values change? Is postgres reachable? Are AWS permissions
   (Pod Identity / IRSA) correct for worker and orders-api (look for `AccessDenied` in logs)?

   ```bash
   helm -n kantyna history kantyna
   kubectl -n kantyna get sa kantyna-worker -o yaml
   ```

## Remediation

| Action | Risk | Command |
|---|---|---|
| Delete a single stuck pod | Safe | `kubectl -n kantyna delete pod <pod>` |
| Restart the deployment | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-<service>` |
| Roll back a bad release | Caution | `helm rollback kantyna <REV> -n kantyna` |
| Increase memory limit (if OOMKilled) | Caution | `helm upgrade ... --reuse-values --set <service>.resources.limits.memory=...` |
| Restart postgres | Caution | `kubectl -n kantyna rollout restart sts/kantyna-postgres` (short full outage) |

## Escalation

- Crash loop of `postgres` or of all `orders-api` replicas: page platform on-call immediately.
- Crash caused by application error after a release: roll back first, then notify the service owner.
