# Kantyna runbooks

Runbooks for alerts defined in the `kantyna` PrometheusRule (`deploy/helm/kantyna/templates/prometheusrule.yaml`).
Each alert links here through its `runbook_url` annotation.

| Alert | Severity | Runbook |
|---|---|---|
| KantynaHighErrorRate | warning | [KantynaHighErrorRate.md](KantynaHighErrorRate.md) |
| KantynaHighLatencyP95 | warning | [KantynaHighLatencyP95.md](KantynaHighLatencyP95.md) |
| KantynaPaymentsFailing | warning | [KantynaPaymentsFailing.md](KantynaPaymentsFailing.md) |
| KantynaPodCrashLooping | critical | [KantynaPodCrashLooping.md](KantynaPodCrashLooping.md) |
| KantynaPodOOMKilled | critical | [KantynaPodOOMKilled.md](KantynaPodOOMKilled.md) |
| KantynaQueueBacklog | warning | [KantynaQueueBacklog.md](KantynaQueueBacklog.md) |
| KantynaDBPoolExhausted | critical | [KantynaDBPoolExhausted.md](KantynaDBPoolExhausted.md) |

## Environment

- Cluster: EKS, `eu-central-1`, namespace `kantyna`, Helm release `kantyna`.
- Services: `orders-api` (FastAPI, :8000), `payments` (Go, :8080), `worker` (SQS consumer, metrics :9000),
  `web` (nginx, :8080), `loadgen` (optional, metrics :9100), `postgres` (StatefulSet, :5432).
- Observability: kube-prometheus-stack (Prometheus, Alertmanager, Grafana), Loki (logs), Tempo (traces).
- Runtime settings: ConfigMap `kantyna-flags` (`flags.json`, mounted at `/etc/kantyna/flags/`), re-read by
  services every ~15s; managed through the `flags:` block in Helm values.

## Conventions

- **Safe** actions: low risk, reversible, can be executed by on-call without approval.
- **Caution** actions: may cause short disruption or data impact; announce in the incident channel first.
- Always record what you did (command + time) in the incident ticket.

## Common commands

```bash
kubectl -n kantyna get pods -o wide
kubectl -n kantyna get events --sort-by=.lastTimestamp | tail -30
helm -n kantyna history kantyna
helm -n kantyna get values kantyna
kubectl -n kantyna get configmap kantyna-flags -o jsonpath='{.data.flags\.json}'
```

Log labels in Loki follow Kubernetes pod labels, e.g. `{namespace="kantyna", app_kubernetes_io_name="orders-api"}`.
