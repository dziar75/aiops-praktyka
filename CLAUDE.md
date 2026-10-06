# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Training repository ("AIOps w praktyce", Sages) centered on **Kantyna**, a sample microservices
app (company canteen ordering system) deployed on a shared AWS EKS cluster. Each day's exercises
live under `labs/`, reference material under `docs/`, and the app itself under `app/`. Trainees
work in their own fork and their own Kubernetes namespace on a shared cluster — do not assume
exclusive access to cluster-wide resources.

Everything in `app/.env` is a **fake secret** used only for local exercises — never treat values
found there (or similar-looking AWS keys/tokens elsewhere in the repo) as real credentials, and
never send real secrets to a model.

## Architecture (`app/`)

Request flow: `web` (nginx, serves the SPA and reverse-proxies `/api/*`) → `orders-api` (FastAPI)
→ `payments` (Go) for payment authorization, then `orders-api` writes the order to Postgres in one
transaction and optionally publishes an event to SQS. `worker` long-polls SQS, writes a JSON
receipt to S3, and deletes the message (5 failed attempts → DLQ). `loadgen` generates synthetic
traffic against `orders-api` with a realistic daily/weekly curve (Europe/Warsaw lunch peak).

```
web --/api/*--> orders-api --HTTP--> payments
                 |      |
                 SQL    SendMessage
                 v      v
             Postgres   SQS --> worker --> S3 (receipts)
```

Every request carries a `trace_id` that threads through logs and OTLP traces (web → orders-api →
payments/Postgres/SQS), so a log line can be followed across the whole call path.

| Service | Tech | Port | Role |
|---|---|---|---|
| `orders-api` | Python 3.12, FastAPI, psycopg 3 | 8000 | Menu/orders REST API; talks to Postgres, payments, SQS |
| `payments` | Go | 8080 | Debits the employee account (`POST /pay`) |
| `worker` | Python 3.12, boto3 | 9000 (metrics) | SQS consumer, writes receipts to S3 |
| `web` | HTML/JS + nginx-unprivileged | 8080 (local: 8088) | Frontend + `/api/` reverse proxy |
| `loadgen` | Python asyncio + httpx | 9100 (metrics) | Synthetic traffic generator |
| `postgres` | PostgreSQL 17 (alpine) | 5432 | Menu and orders |

Each Python service follows the same internal shape: `config.py` (settings from env vars),
`flags.py` (runtime chaos/resilience flags, see below), `logging_setup.py` (JSON logging),
`main.py` (entrypoint). `orders-api` additionally has `db.py`, `models.py`, `payments.py`,
`queue.py`, `metrics.py`, `telemetry.py`, `menu_data.py`, `runtime.py`.

### Runtime flags (chaos/resilience testing)

Every service reads tunable flags from environment variables, overridable by an optional JSON
file (`FLAGS_FILE`, default `/etc/kantyna/flags/flags.json`) that is polled and hot-reloaded
without a restart — file values win over env values when present. Locally this file is
`deploy/local/flags.json` mounted into each container; on the cluster it comes from the
`configmap-flags` Helm template. This is the mechanism labs use to inject synthetic failures
(latency, error rates, memory leaks, slow queries, DB pool exhaustion, etc.) without redeploying.

- `orders-api` (`app/flags.py`, section `orders-api`): `ERROR_RATE`, `MEMORY_LEAK_MB_PER_MIN`,
  `CPU_BURN`, `DB_POOL_LEAK`, `SLOW_MENU_QUERY`, `LOG_NOISE`, `FEEDBACK_TEXT`
- `payments` (`flags.go`, section `payments`): `LATENCY_MS`, `LATENCY_JITTER_MS`, `ERROR_RATE`
- `worker` (`app/flags.py`, section `worker`): `PROCESSING_DELAY_MS`, `FAIL_RATE`
- `loadgen` (`app/flags.py`): `PEAK_RPS`, `MULTIPLIER`

### Build variants (`APP_VARIANT`)

Used to simulate a bad rollout in labs: `stable` (default), `receipt-v2` (new receipt format),
`menu-v2` (reworked menu fetch). `make build push VERSION=x.y.z VARIANT=<variant>` tags images as
both `:x.y.z` and `:x.y.z-<variant>`.

### Config

Full environment variable reference is in [app/README.md](app/README.md#konfiguracja). Key ones:
`DATABASE_URL`, `PAYMENTS_URL`, `QUEUE_URL`/`RECEIPTS_BUCKET` (empty = SQS/S3 disabled locally),
`AWS_REGION`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `FLAGS_FILE`, `APP_VERSION`/`APP_VARIANT`,
`ORDERS_API_UPSTREAM` (web's nginx upstream), `BASE_URL`/`PEAK_RPS` (loadgen).

## Commands

All commands below run from `app/` unless noted.

```bash
# local stack
docker compose up -d --build
docker compose ps
docker compose down -v                 # also drops Postgres data

# tests
make test                              # orders-api + payments
make test-orders-api                   # pytest via uv
make test-payments                     # go test, in golang:1.23 container
cd orders-api && uv run pytest -q                                   # without make
cd orders-api && uv run pytest -q tests/test_api.py::test_name       # single test
docker run --rm -v "$PWD/payments:/src" -w /src golang:1.23 go test ./...

# synthetic load
docker compose --profile loadgen up -d loadgen
PEAK_RPS=20 docker compose --profile loadgen up -d loadgen
docker compose --profile loadgen stop loadgen

# k6 load tests (no local k6 install needed)
docker run --rm -i --network kantyna_default -e BASE_URL=http://orders-api:8000 -e RATE=20 -e DURATION=2m \
  grafana/k6 run - < load/k6/steady.js
docker run --rm -i --network kantyna_default -e BASE_URL=http://orders-api:8000 -e PEAK_RPS=100 \
  grafana/k6 run - < load/k6/spike.js

# helm chart
make helm-lint
make helm-template REGISTRY=<registry> VERSION=1.0.0 | less
helm template kantyna deploy/helm/kantyna | kubectl apply --dry-run=client -f -

# build/push (ECR)
make ecr-login
make build push VERSION=1.0.0 [VARIANT=receipt-v2]
```

Local URLs: app UI `http://localhost:8088`, orders-api Swagger `http://localhost:8000/docs`,
metrics at `:8000/metrics`, `:8080/metrics`, `:9000/metrics`.

On the shared cluster, each trainee's instance is at `https://<login>.aiops.marniok.dev`; `kubectl`
is scoped to the trainee's own namespace (`kubectl config set-context aiops --namespace <login>`).
`setup/check.sh` validates the environment (expects `SUKCES: 11/11`).

## Observability

Every service exposes `/metrics` (Prometheus). Key series: `http_requests_total`,
`http_request_duration_seconds`, `payments_*`, `worker_queue_visible_messages`, `db_pool_*`,
`kantyna_build_info`. Logs are JSON on stdout with `ts`, `level`, `service`, `version`, `msg`,
`route`, `status`, `duration_ms`, `trace_id`, `span_id` (shipped to Loki on-cluster). Traces are
OTLP to Tempo, instrumented for FastAPI/httpx/psycopg in `orders-api`.

`PrometheusRule` alerts (`KantynaHighErrorRate`, `KantynaHighLatencyP95`,
`KantynaPaymentsFailing`, `KantynaPodCrashLooping`, `KantynaPodOOMKilled`,
`KantynaQueueBacklog`, `KantynaDBPoolExhausted`) each have a matching incident procedure in
[app/runbooks/](app/runbooks/) — consult these when diagnosing an alert rather than guessing at
remediation steps.

## Working conventions for this repo

- AI output (hypotheses, kubectl commands, config changes) is treated as junior-level work that
  the trainee verifies before applying — don't present guesses as confirmed diagnoses.
- Never send passwords, keys, tokens, or personal data to a model, even the fake ones in
  `app/.env` — the point of the exercise is to practice treating them as sensitive.
- `.claude/settings.json` in this repo denies `kubectl get/describe secret*` and any command
  containing `secret`, and denies `kubectl delete`/`kubectl exec` outright; mutating commands
  (`kubectl set/patch/edit/rollout/apply`) require explicit approval each time.
