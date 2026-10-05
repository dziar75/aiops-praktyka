# Kantyna

System zamawiania obiadów w firmowej stołówce. Pracownik przegląda menu dnia, składa
zamówienie, płaci kontem pracowniczym i dostaje paragon.

Aplikacja składa się z kilku mikroserwisów, działa na AWS EKS (eu-central-1) i jest w pełni
zinstrumentowana: metryki Prometheus, logi w JSON (Loki) i trace'y OpenTelemetry (Tempo).

## Spis treści

- [Architektura](#architektura)
- [Jak działa zamówienie](#jak-działa-zamówienie)
- [Serwisy](#serwisy)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Testowanie](#testowanie)
- [Konfiguracja](#konfiguracja)
- [Wdrożenie na Kubernetes (Helm)](#wdrożenie-na-kubernetes-helm)
- [Metryki, logi, alerty](#metryki-logi-alerty)
- [Struktura repozytorium](#struktura-repozytorium)

## Architektura

```
                          +-------------------+
   przeglądarka --------> |  web (nginx, SPA) |
                          |       :8080       |
                          +---------+---------+
                                    | /api/*
                                    v
 +--------------+         +-------------------+          +------------------+
 |   loadgen    | ------> |    orders-api     | -------> |    payments      |
 | ruch syntet. |         |  FastAPI  :8000   |   HTTP   |    Go  :8080     |
 |    :9100     |         +----+---------+----+          +------------------+
 +--------------+              |         |
                               | SQL     | SendMessage
                               v         v
                     +-------------+  +-----------+      +-----------+      +----------+
                     | PostgreSQL  |  |  AWS SQS  | ---> |  worker   | ---> |  AWS S3  |
                     |  17  :5432  |  |  orders   |      |   :9000   |      | paragony |
                     +-------------+  +-----------+      +-----------+      +----------+

 Observability (w klastrze):
   Prometheus + Alertmanager + Grafana  <- /metrics z każdego serwisu
   Loki                                 <- logi JSON ze wszystkich podów
   Tempo                                <- trace'y OTLP
```

## Jak działa zamówienie

1. **web** serwuje stronę (HTML/JS) i przekazuje wszystkie wywołania `/api/*` do `orders-api`.
2. **orders-api** przy starcie tworzy schemat bazy i wypełnia menu (ok. 20 dań), jeśli jest puste.
3. `POST /api/orders` w `orders-api`:
   1. waliduje zamówienie (`employee_id` jako tekst, np. `"e-42"`, oraz lista pozycji `menu_item_id` + `qty`),
   2. liczy kwotę na podstawie cen z bazy,
   3. woła **payments** (`POST /pay`). Odmowa płatności kończy zamówienie błędem i nic nie trafia do bazy,
   4. zapisuje zamówienie i pozycje w **PostgreSQL** w jednej transakcji,
   5. publikuje zdarzenie do kolejki **SQS** (tylko gdy ustawiono `QUEUE_URL`).
4. **worker** odbiera zdarzenia z SQS (long polling), „przygotowuje” zamówienie, zapisuje
   paragon w JSON do **S3** (`receipts/RRRR/MM/DD/<order_id>.json`) i usuwa wiadomość z kolejki.
   Gdy przetwarzanie się nie uda, wiadomość wraca do kolejki, a po 5 próbach trafia do DLQ.
5. **loadgen** generuje ruch o realistycznym profilu dobowym (czas Europe/Warsaw): w nocy ok.
   0,5 req/s, szczyt w porze obiadowej 11:30–13:30, w weekend ok. 30% ruchu. Ruch to w 60%
   przeglądanie menu, 10% wyszukiwanie, 25% zamówienia i 5% sprawdzanie statusu.

Każde żądanie dostaje `trace_id`, który pojawia się w logach i w trace'ach, więc z wpisu w logu
można przejść do całej ścieżki żądania (web → orders-api → payments / Postgres / SQS).

## Serwisy

| Serwis       | Technologia                     | Port              | Rola |
|--------------|---------------------------------|-------------------|------|
| `orders-api` | Python 3.12, FastAPI, psycopg 3 | 8000              | REST API menu i zamówień; Postgres, payments, SQS |
| `payments`   | Go                              | 8080              | Obciążenie konta pracownika (`POST /pay`) |
| `worker`     | Python 3.12, boto3              | 9000 (metryki)    | Konsument SQS, paragony do S3 |
| `web`        | HTML/JS, nginx-unprivileged     | 8080 (lokalnie 8088) | Frontend + proxy `/api/` |
| `loadgen`    | Python asyncio + httpx          | 9100 (metryki)    | Ruch syntetyczny |
| `postgres`   | PostgreSQL 17 (alpine)          | 5432              | Menu i zamówienia |

### Endpointy `orders-api`

| Metoda | Ścieżka                  | Opis |
|--------|--------------------------|------|
| GET    | `/healthz`               | Liveness |
| GET    | `/readyz`                | Readiness (sprawdza połączenie z bazą) |
| GET    | `/version`               | Wersja i wariant builda |
| GET    | `/api/menu`              | Menu dnia (`{"items": [...]}`) |
| GET    | `/api/menu/search?q=`    | Wyszukiwanie w menu po nazwie i kategorii |
| POST   | `/api/orders`            | Złożenie zamówienia |
| GET    | `/api/orders/{id}`       | Status zamówienia |
| GET    | `/metrics`               | Metryki Prometheus |
| GET    | `/docs`                  | Swagger UI (OpenAPI) |

## Uruchomienie lokalne

Wymagania: Docker z Compose v2. Opcjonalnie `jq`, `uv` (testy Pythona) i `make`.

```bash
docker compose up -d --build
docker compose ps
```

| Co | Adres |
|----|-------|
| Aplikacja (UI) | <http://localhost:8088> |
| Swagger orders-api | <http://localhost:8000/docs> |
| Metryki orders-api / payments / worker | `localhost:8000/metrics`, `localhost:8080/metrics`, `localhost:9000/metrics` |

Lokalnie nie ma SQS ani S3, więc worker startuje i czeka (wpisuje to do logów). Zamówienia
i tak przechodzą przez payments i trafiają do bazy.

Zatrzymanie (razem z danymi bazy):

```bash
docker compose down -v
```

## Testowanie

### 1. Ręcznie w przeglądarce

Otwórz <http://localhost:8088>, dodaj kilka dań do koszyka, wpisz numer pracownika i kliknij
**Zamów**. Numer zamówienia trafia do pola statusu, gdzie można śledzić jego stan.

### 2. Smoke test API (curl)

```bash
curl -s localhost:8000/healthz
curl -s localhost:8000/readyz
curl -s localhost:8000/version

curl -s localhost:8000/api/menu | jq '.items[:3]'
curl -s 'localhost:8000/api/menu/search?q=pierog' | jq

ORDER_ID=$(curl -s -X POST localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"employee_id": "e-42", "items": [{"menu_item_id": 1, "qty": 2}]}' | jq -r .id)
curl -s "localhost:8000/api/orders/${ORDER_ID}" | jq
```

Oczekiwany wynik: `POST` zwraca `201` z `id`, `total_pln` i `transaction_id` z payments.
Błędne dane (np. pusta lista `items` albo `qty` > 50) dają `422` z opisem błędu walidacji.

To samo przez frontend (sprawdza proxy nginx):

```bash
curl -s localhost:8088/api/menu | jq '.items | length'
```

### 3. Testy jednostkowe

```bash
make test               # wszystko
make test-orders-api    # pytest (uv) — API, walidacja, flagi
make test-payments      # go test w kontenerze golang:1.23
```

Bez `make`:

```bash
cd orders-api && uv run pytest -q
docker run --rm -v "$PWD/payments:/src" -w /src golang:1.23 go test ./...
```

### 4. Ruch i testy obciążeniowe

Ciągły ruch o profilu dobowym (loadgen):

```bash
docker compose --profile loadgen up -d loadgen
PEAK_RPS=20 docker compose --profile loadgen up -d loadgen   # mocniej
docker compose --profile loadgen stop loadgen
```

Jednorazowe testy k6 (bez instalacji k6, w kontenerze w sieci Compose):

```bash
# stałe obciążenie: RATE req/s przez DURATION
docker run --rm -i --network kantyna_default \
  -e BASE_URL=http://orders-api:8000 -e RATE=20 -e DURATION=2m \
  grafana/k6 run - < load/k6/steady.js

# skok ruchu: 10 → PEAK_RPS req/s, ok. 6 min, próg p95 < 500 ms dla menu
docker run --rm -i --network kantyna_default \
  -e BASE_URL=http://orders-api:8000 -e PEAK_RPS=100 \
  grafana/k6 run - < load/k6/spike.js
```

### 5. Metryki, logi, trace'y

```bash
# ruch i błędy per endpoint
curl -s localhost:8000/metrics | grep -E '^http_requests_total'
# biznes: liczba i wartość zamówień
curl -s localhost:8000/metrics | grep -E '^(orders_created_total|order_value_pln_total)'
# pula połączeń do bazy
curl -s localhost:8000/metrics | grep -E '^db_pool'
# payments
curl -s localhost:8080/metrics | grep -E '^payments_'

# logi JSON (jedna linia = jeden obiekt)
docker compose logs -f orders-api
docker compose logs orders-api --no-log-prefix | grep '^{' | jq -c '{ts, level, msg, route, status, duration_ms, trace_id}'
```

### 6. Chart Helm

```bash
make helm-lint
make helm-template REGISTRY=<registry> VERSION=1.0.0 | less
helm template kantyna deploy/helm/kantyna | kubectl apply --dry-run=client -f -
```

## Konfiguracja

### Zmienne środowiskowe

| Zmienna           | Serwis             | Opis | Domyślnie lokalnie |
|-------------------|--------------------|------|--------------------|
| `DATABASE_URL`    | orders-api         | Connection string do Postgresa | `postgresql://kantyna:kantyna@postgres:5432/kantyna` |
| `PAYMENTS_URL`    | orders-api         | Adres serwisu payments | `http://payments:8080` |
| `QUEUE_URL`       | orders-api, worker | URL kolejki SQS (pusty = wyłączone) | brak |
| `RECEIPTS_BUCKET` | worker             | Bucket S3 na paragony | brak |
| `AWS_REGION`      | orders-api, worker | Region AWS | `eu-central-1` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | orders-api | Endpoint OTLP dla trace'ów (pusty = bez eksportu) | brak |
| `FLAGS_FILE`      | wszystkie          | Ścieżka do pliku z flagami | `/etc/kantyna/flags/flags.json` |
| `APP_VERSION`     | wszystkie (build)  | Wersja w `/version` i metrykach | `0.0.0-dev` |
| `APP_VARIANT`     | wszystkie (build)  | Wariant builda | `stable` |
| `ORDERS_API_UPSTREAM` | web            | Upstream nginx dla `/api/` | `orders-api:8000` |
| `BASE_URL`        | loadgen            | Adres docelowy ruchu | `http://orders-api:8000` |
| `PEAK_RPS`        | loadgen            | Req/s w szczycie obiadowym | `5` |

### Warianty builda (`APP_VARIANT`)

| Wariant      | Opis |
|--------------|------|
| `stable`     | Domyślny build produkcyjny |
| `receipt-v2` | Nowy format paragonu (dane do faktury) |
| `menu-v2`    | Przebudowane pobieranie menu |

## Wdrożenie na Kubernetes (Helm)

Chart: [`deploy/helm/kantyna`](deploy/helm/kantyna).

```bash
make ecr-login
make build push VERSION=1.0.0

helm upgrade --install kantyna deploy/helm/kantyna \
  --namespace <namespace> --create-namespace \
  --set global.imageRegistry=<account>.dkr.ecr.eu-central-1.amazonaws.com \
  --set global.imageTag=1.0.0 \
  --set global.queueUrl=<sqs-url> \
  --set global.receiptsBucket=<bucket> \
  --set metrics.serviceMonitor.enabled=true \
  --set prometheusRule.enabled=true
```

- Uprawnienia do SQS i S3 dają role IAM przypięte przez **EKS Pod Identity** do ServiceAccountów
  `kantyna-orders-api` i `kantyna-worker`.
- Wariant builda: `make build push VERSION=1.1.0 VARIANT=receipt-v2` (tagi `:1.1.0` i `:1.1.0-receipt-v2`).
- Wycofanie wydania: `helm rollback kantyna -n <namespace>`.

## Metryki, logi, alerty

- Każdy serwis wystawia `/metrics` (orders-api `:8000`, payments `:8080`, worker `:9000`,
  loadgen `:9100`). Na klastrze Prometheus zbiera je przez `ServiceMonitor`.
- Najważniejsze sygnały: ruch, błędy i latencja per endpoint (`http_requests_total`,
  `http_request_duration_seconds`), płatności (`payments_*`), backlog kolejki
  (`worker_queue_visible_messages`), pula połączeń (`db_pool_*`), wersja (`kantyna_build_info`).
- Logi: JSON na stdout z polami `ts`, `level`, `service`, `version`, `msg`, `route`, `status`,
  `duration_ms`, `trace_id`, `span_id` (zbiera je Loki).
- Trace'y: OTLP do Tempo (orders-api, z instrumentacją FastAPI, httpx i psycopg).
- Alerty (`PrometheusRule`): `KantynaHighErrorRate`, `KantynaHighLatencyP95`,
  `KantynaPaymentsFailing`, `KantynaPodCrashLooping`, `KantynaPodOOMKilled`,
  `KantynaQueueBacklog`, `KantynaDBPoolExhausted`. Procedury dla każdego alertu są w
  [`runbooks/`](runbooks/).

## Struktura repozytorium

```
.
├── orders-api/            # FastAPI: menu i zamówienia (+ testy pytest)
├── payments/              # Go: płatności (+ go test)
├── worker/                # konsument SQS, paragony do S3
├── web/                   # frontend + nginx
├── loadgen/               # generator ruchu syntetycznego
├── load/k6/               # scenariusze k6 (steady, spike)
├── deploy/
│   ├── helm/kantyna/      # chart Helm
│   └── local/flags.json   # flagi runtime dla Docker Compose
├── runbooks/              # procedury dla alertów
├── scripts/               # skrypty operacyjne (backup bazy)
├── docker-compose.yml
└── Makefile
```
