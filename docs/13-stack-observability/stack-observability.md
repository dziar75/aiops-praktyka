# Stack observability: metryki, logi, ślady i alerty

Opis do diagramu [`architektura.html`](architektura.html) (pobierz i otwórz w przeglądarce). Pokazuje, skąd Grafana bierze dane, z których korzystasz w lab05 i lab07.

## Trzy sygnały, trzy magazyny

Wszystko działa w namespace `monitoring` i jest wspólne dla klastra. Dane swojej Kantyny wybierasz etykietą `namespace`.

| Sygnał | Jak dociera | Magazyn | Język zapytań | Retencja |
|---|---|---|---|---|
| Metryki | Prometheus sam pobiera `/metrics` z podów (ServiceMonitor), do tego kube-state-metrics i node-exporter | Prometheus | PromQL | 21 dni |
| Logi | Kantyna pisze JSON na stdout, Alloy (DaemonSet) czyta pliki logów z węzła | Loki | LogQL | 21 dni |
| Zdarzenia K8s | Alloy events czyta zdarzenia z API Kubernetes (K8s trzyma je tylko ok. 1 h) | Loki, `{job="kubernetes-events"}` | LogQL | 21 dni |
| Ślady | orders-api wysyła spany przez OpenTelemetry SDK prosto do Tempo (OTLP gRPC `:4317`) | Tempo | TraceQL | 7 dni |

## OpenTelemetry: tylko ślady, bez kolektora

- **orders-api** ma OpenTelemetry SDK z automatyczną instrumentacją FastAPI, httpx (wywołania payments) i psycopg (zapytania do Postgresa). Span z zapytaniem SQL widzisz więc w śladzie żądania.
- Adres trafia do podów ze zmiennej `OTEL_EXPORTER_OTLP_ENDPOINT` (`http://tempo.monitoring.svc:4317`). Nazwa serwisu: `OTEL_SERVICE_NAME`.
- **payments** (Go) i **worker** dostają tę zmienną, ale nie wysyłają śladów. W śladzie zamówienia payments widać tylko jako span klienta HTTP z orders-api.
- Nie ma OpenTelemetry Collectora: aplikacja wysyła prosto do Tempo. Metryki i logi nie idą przez OTLP. Metryki zbiera Prometheus (`/metrics`), logi Alloy (stdout).

## Co robi Alloy z logami

Z każdej linii logu JSON wyciąga pole `level` jako **etykietę** (można filtrować `{level="ERROR"}`) i `trace_id` jako **metadane** (nie jest etykietą, więc nie zwiększa liczby strumieni). Etykiety dodaje też z Kubernetesa: `namespace`, `pod`, `container`, `app`, `node`.

## Z logu do śladu i z powrotem

Grafana ma źródła Prometheus, Loki i Tempo powiązane ze sobą:
- w logu z polem `trace_id` jest link do śladu w Tempo,
- w śladzie jest przycisk do logów z tego samego `trace_id`,
- Tempo liczy z śladów metryki (service graph, czasy spanów) i zapisuje je w Prometheusie.

## Droga alertów

1. Reguły alertów to `PrometheusRule`. Są włączone tylko w namespace `demo`. W Twoim namespace metryki są zbierane, ale alertów nie ma.
2. Prometheus przekazuje je do Alertmanagera, który grupuje powiadomienia.
3. Alertmanager wysyła webhook do `alert-log`: powiadomienie zapisane jako linia JSON, więc trafia do Loki (`{container="alert-log"} | json`). Alerty z `demo` idą też do Robusty.

## Kto czyta dane

- **Ty:** `https://grafana.aiops.marniok.dev` z konta z karty (rola Editor: Explore, dashboardy, alerty). Dostęp tylko z adresów IP z listy. Źródła danych są tylko do odczytu.
- **Claude Code:** przez `gcx` (CLI) albo `mcp-grafana` (serwer MCP), po tym samym koncie. Porównanie: [`mcp-grafana-vs-gcx.md`](../09-grafana-elastic-ai/mcp-grafana-vs-gcx.md). Każde zapytanie od AI sprawdzasz w Explore.

## Zapytania na start

```promql
sum by (route) (rate(http_requests_total{namespace="demo"}[5m]))
```

```logql
{namespace="demo", app="orders-api"} | json | level="ERROR"
```
