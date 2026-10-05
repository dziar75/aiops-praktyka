# KantynaQueueBacklog

**Severity:** warning
**Condition:** `worker_queue_visible_messages` > 50 for 10 minutes.

## Symptoms

- Orders are accepted by `orders-api` but stay "pending" (receipts not generated, kitchen not notified).
- SQS `ApproximateNumberOfMessagesVisible` grows; age of oldest message rises.

## Impact

Order confirmations and receipts are delayed. No data loss as long as messages stay within SQS retention.

## Diagnosis

1. Backlog and throughput:

   ```promql
   max(worker_queue_visible_messages{namespace="kantyna"})
   sum by (result) (rate(worker_messages_processed_total{namespace="kantyna"}[5m]))
   histogram_quantile(0.95, sum by (le) (rate(worker_processing_seconds_bucket{namespace="kantyna"}[5m])))
   sum by (operation, code) (rate(worker_aws_errors_total{namespace="kantyna"}[5m]))
   ```

   Compare incoming rate (orders created) with processed rate. Processing time up -> worker is slow;
   processed `result="failed"` up -> messages are retried; AWS errors -> permissions/network.

2. Worker pods:

   ```bash
   kubectl -n kantyna get pods -l app.kubernetes.io/name=worker
   kubectl -n kantyna logs deploy/kantyna-worker --since=15m --tail=200
   ```

   ```logql
   {namespace="kantyna", app_kubernetes_io_name="worker"} | json | level=~"WARNING|ERROR"
   sum by (level) (count_over_time({namespace="kantyna", app_kubernetes_io_name="worker"} | json [5m]))
   ```

3. Queue state in AWS:

   ```bash
   aws sqs get-queue-attributes --region eu-central-1 --queue-url "$QUEUE_URL" \
     --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
   ```

4. Runtime settings for the worker section: `kubectl -n kantyna get configmap kantyna-flags -o jsonpath='{.data.flags\.json}' | jq .worker`.

## Remediation

| Action | Risk | Command |
|---|---|---|
| Scale out worker | Safe | `kubectl -n kantyna scale deploy/kantyna-worker --replicas=3` |
| Restart worker (stuck consumer) | Safe | `kubectl -n kantyna rollout restart deploy/kantyna-worker` |
| Revert worker settings | Safe | restore previous `flags.worker` values via `helm upgrade ... --reuse-values` |
| Roll back release | Caution | `helm rollback kantyna <REV> -n kantyna` |
| Purge the queue | **Do not** without owner approval | orders would be lost |

Scale back to the configured replica count (`helm upgrade --reuse-values`) once the backlog is drained.

## Escalation

- Backlog > 500 or oldest message > 30 min: notify the orders-api/worker owner.
- AWS `AccessDenied` / throttling: escalate to platform on-call (Pod Identity association, SQS limits).
