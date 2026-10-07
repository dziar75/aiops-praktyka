# Wykrywanie anomalii — Azure Monitor, Grafana ML i AWS

Materiał pomocniczy do szkolenia „AIOps w praktyce”. Diagram architektury: [`architektura.html`](architektura.html).

> Stan na 1 października 2026. W tej kategorii dużo się dzieje: Azure AI Anomaly Detector został wycofany **1.10.2026**, a Amazon DevOps Guru przestaje przyjmować nowych klientów **29.10.2026**. Sprawdź linki w sekcji Źródła, zanim z nich skorzystasz.

---

## TL;DR

| | **Azure Monitor** | **Grafana ML** (Grafana Cloud) | **AWS (CloudWatch)** |
|---|---|---|---|
| **Główna funkcja** | *Dynamic thresholds* w regułach alertów (metryki, logi, PromQL) | *Forecasting* i *Outlier detection* na dowolnym wspieranym źródle danych + Sift | *Anomaly Detection* na metrykach (pasmo oczekiwanych wartości) + *Logs Anomaly Detection* |
| **Warstwa AI (LLM)** | Azure Copilot / investigations w Azure Monitor | Grafana Assistant + Investigations | **CloudWatch investigations** |
| **Co uczy się wzorca** | 10 dni historii, sezonowość dzienna; tygodniowa po 3 tygodniach | Historia serii (do 50k punktów), sezonowość konfigurowalna | Do 2 tygodni historii, sezonowość dzienna i tygodniowa |
| **Działa na danych z** | Tylko Azure (metryki platformy, Log Analytics, Azure Monitor Prometheus) | Prometheus, Loki, Graphite, InfluxDB, Elasticsearch, Postgres, BigQuery, Datadog, Splunk… | Tylko CloudWatch (metryki AWS, Container Insights, custom metrics, Logs) |
| **Koszt AD** | Płatne jak alert (cena per monitorowana seria) | **Za darmo** w każdym planie Grafana Cloud (z limitami) | 0,30 USD/mies. za alarm AD (standard); Logs AD **bez dopłaty** |
| **Wycofane / wygaszane** | ❌ Azure AI Anomaly Detector (koniec: **1.10.2026**), ❌ Metrics Advisor | — | ❌ Lookout for Metrics (10.2025), ⚠️ **DevOps Guru** (brak nowych klientów od 29.10.2026, koniec 30.09.2027) |

**Najkrócej:** „klasyczne” wykrywanie anomalii (ML na szeregach czasowych) jest dziś **wbudowane w alerting** każdej platformy. Osobne usługi typu „Anomaly Detector API” znikają. Nad nim powstaje nowa warstwa: **agenty AI do dochodzeń** (CloudWatch investigations, Grafana Investigations, Azure Monitor investigations), które korzystają z wykrytych anomalii jako sygnału.

**Odpowiednik Azure Monitor anomaly detection w AWS:**
- **Amazon CloudWatch Anomaly Detection**, czyli alarmy z pasmem `ANOMALY_DETECTION_BAND` (odpowiednik *dynamic thresholds*),
- **CloudWatch Logs Anomaly Detection** (anomalie we wzorcach logów),
- **CloudWatch investigations** (agent AI do analizy przyczyn).

DevOps Guru był „AIOps-owym” odpowiednikiem, ale jest wygaszany, więc **nie warto na nim niczego nowego budować**.

---

## 1. Do czego służą?

### Azure Monitor

- **Dynamic thresholds:** zamiast stałego progu („CPU > 80%”) model ML uczy się normalnego zachowania metryki (sezonowość godzinowa, dzienna, tygodniowa) i alarmuje, gdy wartość wyjdzie poza wyliczone pasmo. Działa na:
  - metrykach platformy i custom metrics (alerty metryczne),
  - wynikach zapytań KQL (alerty log search),
  - wyrażeniach **PromQL** z Azure Monitor managed Prometheus (preview).
  Jedna reguła obejmuje setki serii (np. wszystkie VM w subskrypcji).
- **Application Insights Smart Detection / Failure Anomalies:** automatyczne wykrywanie nietypowego wzrostu odsetka błędów, spadku wydajności czy wycieków pamięci w aplikacji. Microsoft przenosi te mechanizmy do standardowych reguł alertów.
- **Funkcje KQL** (`series_decompose_anomalies`, `series_decompose_forecast`): wykrywanie anomalii i prognozy bezpośrednio w zapytaniach Log Analytics, bez dodatkowej usługi.
- **Warstwa AI:** Azure Copilot (agent observability) i *issues/investigations* w Azure Monitor analizują alert i podsuwają hipotezy przyczyn.
- ❌ **Azure AI Anomaly Detector** (API do wykrywania anomalii w dowolnych szeregach) został **wycofany 1.10.2026**. Microsoft kieruje do Microsoft Fabric albo open-source'owego `microsoft/anomaly-detector`. Jeśli ktoś na szkoleniu o niego zapyta, to właśnie ta usługa.

### Grafana ML (Grafana Cloud)

- **Metric forecasting:** model (Prophet-like) uczy się historii serii, prognozuje przyszłe wartości i wyznacza **pasmo ufności**. Wyjście poza pasmo to anomalia. Z prognozy da się zrobić **alert** (Grafana Alerting) albo panel na dashboardzie. Przykłady zastosowań:
  - wykrycie nietypowego ruchu,
  - prognoza zapełnienia dysku (*capacity planning*).
- **Outlier detection:** wykrywa, który członek grupy zachowuje się inaczej niż reszta (np. 1 pod z 20 replik ma 3× większą latencję). Algorytmy: DBSCAN i MAD.
- **Sift:** automatyczna diagnostyka w Kubernetes. Uruchamia zestaw sprawdzeń: błędy w logach, „hałaśliwi sąsiedzi”, skoki zasobów, korelacja z deployami, crashujące pody.
- **Dynamic alerting** i integracja z **Grafana Assistant / Investigations**: anomalie mogą być punktem startu dochodzenia AI.
- Działa na **wielu źródłach danych**, nie tylko w ekosystemie Grafany. To główna przewaga nad chmurowymi natywnymi rozwiązaniami.

### AWS

- **CloudWatch Anomaly Detection (metryki):** model uczy się do 2 tygodni historii metryki (z sezonowością dzienną i tygodniową) i wyznacza pasmo oczekiwanych wartości. Używa się go w:
  - **alarmach** (`GreaterThanUpperThreshold`, `LessThanLowerThreshold`, `LessThanLowerOrGreaterThanUpperThreshold`),
  - na wykresach (funkcja `ANOMALY_DETECTION_BAND(m1, 2)`).
  Działa na metrykach AWS, **Container Insights** (EKS/ECS), custom metrics i metric math.
- **CloudWatch Logs Anomaly Detection:** *log anomaly detector* na grupie logów uczy się wzorców komunikatów. Wykrywa nowe wzorce, nagłe wzrosty lub spadki częstotliwości i zmiany w tokenach (np. nowy kod błędu). Dostępny też ad hoc w Logs Insights (`| pattern @message | anomaly`).
- **CloudWatch investigations:** asystent generatywnego AI do incydentów. Startuje z alarmu, metryki lub zapytania Logs Insights. Analizuje metryki, logi, zdarzenia CloudTrail (zmiany), AWS Health, X-Ray, Application Signals i zasoby EKS. Buduje hipotezy przyczyny i może zaproponować runbook SSM Automation. To odpowiednik Grafana Investigations i Azure Monitor investigations.
- Inne usługi z „anomaly detection” w nazwie (na marginesie):
  - **Amazon OpenSearch Service anomaly detection:** algorytm Random Cut Forest na danych w OpenSearch. Odpowiednik ML w Elasticu.
  - **AWS Cost Anomaly Detection:** anomalie w kosztach. Od 2026 z analizą przyczyn przez AI.
  - **Amazon GuardDuty:** anomalie w kontekście bezpieczeństwa.
- ⚠️ **Amazon DevOps Guru:** w pełni zarządzany AIOps (anomalie i „insights” dla zasobów z CloudFormation/tagów). Usługa jest wygaszana: **od 29.10.2026 brak nowych klientów**, koniec wsparcia **30.09.2027**. AWS zaleca przejście na sygnały z CloudWatch.
- ❌ **Amazon Lookout for Metrics:** wyłączony 10.10.2025.

---

## 2. Czym się różnią?

| Wymiar | Azure Monitor | Grafana ML | AWS CloudWatch |
|---|---|---|---|
| **Model działania** | Dynamiczny próg w regule alertu | Osobny obiekt „forecast” / „outlier detector”, którego wynik idzie do alertu lub dashboardu | Detektor anomalii przypisany do metryki + alarm na pasmie |
| **Konfiguracja wrażliwości** | Low / Medium / High + liczba naruszeń w oknie (np. 2 z 4) | Parametry modelu, przedział ufności, sezonowość, czas treningu | Szerokość pasma (liczba odchyleń standardowych, np. 2), okresy wykluczone z treningu |
| **Wykluczanie awarii z treningu** | Automatycznie (+ data startu nauki) | Ręcznie (zakres treningu) | Ręcznie: *excluded time ranges* |
| **Wykrywanie „outliera w grupie”** | Brak natywnie (można KQL) | ✅ Outlier detection | Brak natywnie (metric math / Contributor Insights) |
| **Anomalie w logach** | KQL (`series_decompose_anomalies`) na zliczeniach | Przez metryki z Loki (LogQL → forecast) | ✅ Natywny log anomaly detector (wzorce) |
| **Multi-cloud / on-prem** | ❌ Tylko Azure | ✅ Dowolne wspierane źródło | ❌ Tylko CloudWatch (dane spoza AWS trzeba wysłać jako custom metrics) |
| **Analiza przyczyn przez AI** | Azure Copilot / Azure Monitor investigations | Grafana Assistant Investigations, Sift | CloudWatch investigations |
| **Próg wejścia** | Niski (checkbox „Dynamic” w alercie) | Niski (UI), ale potrzebne konto Grafana Cloud | Niski (przycisk przy metryce lub CLI/Terraform) |

**Wspólne ograniczenia wszystkich trzech:**
- Potrzebują **historii**. Nowa usługa przez pierwsze dni lub tygodnie nie ma sensownego pasma.
- Wykrywają **gwałtowne odchylenia**, a słabo radzą sobie z powolnym dryfem (np. wyciek pamięci przez 2 tygodnie staje się „nową normą”).
- Metryki rzadkie lub binarne (0/1, liczba podów) słabo się nadają, a część z nich jest wprost niewspierana (lista w dokumentacji Azure).
- **Anomalia ≠ problem.** Black Friday, kampania marketingowa czy batch raz w miesiącu dają fałszywe alarmy, jeśli model ich nie zna.

---

## 3. Jaką mają opinię?

### Azure Monitor (dynamic thresholds)

- **Plusy:** najprostsze w użyciu (jeden przełącznik w regule), dobre do „masowego” alertingu na setkach zasobów, gdy nie wiadomo, jaki próg ustawić.
- **Minusy:**
  - mało przejrzyste: nie wiadomo, *dlaczego* pasmo jest takie, a nie inne,
  - przy metrykach o małej zmienności bywa hałaśliwe,
  - brak dynamic thresholds w regułach z wieloma warunkami,
  - wygaszenie Anomaly Detector i Metrics Advisor zostawiło część klientów bez zamiennika ogólnego przeznaczenia.

### Grafana ML

- **Plusy:**
  - **darmowe** w Grafana Cloud,
  - działa na danych z wielu źródeł,
  - outlier detection dobrze oceniane w Kubernetesie (wyłapuje „ten jeden zły pod”),
  - forecast przydatny do capacity planningu.
- **Minusy:**
  - **tylko Grafana Cloud** (brak w OSS i w Amazon Managed Grafana),
  - limity (10 prognoz, 10 detektorów na instancję),
  - model wymaga strojenia, inaczej przy sezonowych danych bywa dużo fałszywych alarmów,
  - nie każde źródło danych jest wspierane (np. CloudWatch nie ma na oficjalnej liście).

### AWS CloudWatch

- **Plusy:**
  - natywne, tanie, łatwe w Terraformie/CloudFormation,
  - **Logs Anomaly Detection bez dopłaty** i według społeczności zaskakująco użyteczne (wyłapuje nowe typy błędów po deployu),
  - CloudWatch investigations dobrze korelują zmiany z CloudTrail z incydentem.
- **Minusy:**
  - alarmy AD bywają hałaśliwe przy metrykach z dużym rozrzutem i często trzeba je stroić (szerokość pasma, `EvaluationPeriods`, `DatapointsToAlarm`),
  - model trzeba „uczyć” po awariach (*excluded time ranges*),
  - działa tylko na danych w CloudWatch,
  - wygaszanie kolejnych usług AIOps (Lookout for Metrics, DevOps Guru) obniża zaufanie do długoterminowych inwestycji w „specjalne” usługi AWS. CloudWatch jest tu najbezpieczniejszym wyborem.

---

## 4. Czy są bezpieczne?

Klasyczne wykrywanie anomalii (dynamic thresholds, forecast, CloudWatch AD) to **ML na szeregach czasowych bez LLM**. Dane nie trafiają do modeli generatywnych, są przetwarzane w tej samej usłudze, w której już leżą. Ryzyko pojawia się w dwóch miejscach:

| Ryzyko | Azure | Grafana ML | AWS |
|---|---|---|---|
| **Dane opuszczają środowisko?** | Nie (zostają w Azure Monitor) | **Tak**: metryki muszą trafić do Grafana Cloud (wysyłka przez remote_write lub zapytania do Twojego źródła danych) | Nie (zostają w CloudWatch, w regionie) |
| **Warstwa LLM (investigations)** | Azure Copilot w ramach tenantu Microsoft | Backend Grafana Cloud + LLM dostawcy Grafany | CloudWatch investigations (Amazon Bedrock w AWS). Każda akcja w **CloudTrail**, działa z uprawnieniami zalogowanego użytkownika lub wskazanej roli IAM |
| **Uprawnienia** | Azure RBAC (Monitoring Contributor/Reader) | Grafana RBAC + uprawnienia konta serwisowego do źródeł danych | IAM: `cloudwatch:PutAnomalyDetector`, `logs:CreateLogAnomalyDetector`; dla investigations polityki `AIOps*` i rola z odczytem zasobów |
| **Ryzyka operacyjne** | Fałszywe alarmy → *alert fatigue*; brak alarmu przy powolnym dryfie | j.w. + limity ML | j.w. + model uczony na okresie awarii uzna awarię za normę |

Na co uważać:
- **Logi w Logs Anomaly Detection** mogą zawierać PII. Anomalie (z przykładowymi liniami logów) widzi każdy z dostępem do konsoli. Stosuj CloudWatch Logs *data protection policies* (maskowanie).
- **CloudWatch investigations** po skonfigurowaniu okresowo skanuje zasoby konta rolą IAM, a dla niektórych usług wywołuje `kms:Decrypt`. Daj jej minimalne uprawnienia read-only i sprawdź, czy dostępność w regionie nie wymaga przetwarzania poza UE (*cross-region inference*).
- **Grafana Cloud:** wybierz region EU stacka i sprawdź DPA.
- **Auto-remediacja** (runbooki SSM z investigations, akcje z alertów) tylko z akceptacją człowieka.

---

## 5. Licencje i koszty

### Azure Monitor

| Element | Koszt |
|---|---|
| Alert metryczny z dynamic thresholds | płatny per monitorowana seria czasowa / miesiąc; dynamiczny próg jest droższy niż statyczny (sprawdź aktualny cennik Azure Monitor) |
| Alert log search z dynamic threshold | jak zwykły alert log search (per reguła × częstotliwość) |
| Funkcje KQL (`series_decompose_anomalies`) | brak dopłaty, płacisz za ingest i zapytania Log Analytics |
| Smart Detection (App Insights) | w cenie App Insights |
| Licencja | brak, model pay-as-you-go w subskrypcji Azure |

### Grafana ML

| Element | Koszt |
|---|---|
| Forecasting, outlier detection, Sift | **0 zł w każdym planie Grafana Cloud, także Free** |
| Metryki generowane przez ML | nie wliczają się do billable series |
| Limity | 10 prognoz × 100 serii, 10 detektorów × 1000 serii na instancję (więcej po kontakcie z Grafaną) |
| Dane źródłowe | wg planu Grafana Cloud (Free: 10k serii metryk, 50 GB logów, retencja 14 dni) |
| Self-hosted Grafana OSS / Amazon Managed Grafana | ❌ Grafana ML niedostępne |

### AWS

| Element | Koszt |
|---|---|
| Alarm z anomaly detection | **0,30 USD/mies.** za alarm (standard resolution; liczony jak 3 metryki: wartość + górne i dolne pasmo), 0,90 USD przy high resolution |
| Pasmo AD tylko na wykresie (bez alarmu) | bez dopłaty poza zapytaniami `GetMetricData` |
| Logs Anomaly Detection | **bez dodatkowej opłaty**: w cenie ingestii logów (0,50 USD/GB). Wzorce/porównania w Logs Insights jak zwykłe zapytania (0,005 USD/GB skanowany) |
| CloudWatch investigations | **bez dodatkowej opłaty** (limit: 150 rozszerzonych dochodzeń/mies. na konto, 2 równoległe). Mogą powstać drobne koszty API (CloudWatch, X-Ray, Cloud Control, SNS) |
| Container Insights (metryki EKS do AD) | płatne jak custom metrics / Logs; *enhanced observability* rozliczane per obserwacja |
| Free Tier CloudWatch | 10 alarmów, 10 custom metrics, 5 GB logów/mies. |
| DevOps Guru | per zasób/godz. + API, ale **od 29.10.2026 niedostępny dla nowych kont** |

**Koszt eksperymentu na AWS:** płatne licencje **nie są potrzebne**. Koszt to grosze: kilka alarmów AD × 0,30 USD plus ingest logów. Grafana ML działa na darmowym koncie Grafana Cloud.

---

## 6. Instalacja i użycie

### 6.1 AWS: CloudWatch Anomaly Detection na metryce (CLI)

**Przygotowanie (EKS):** włącz Container Insights, żeby mieć metryki podów i węzłów:

```bash
aws eks create-addon --cluster-name lab-eks --addon-name amazon-cloudwatch-observability
# Metryki pojawią się w przestrzeni nazw ContainerInsights (np. pod_cpu_utilization, pod_number_of_container_restarts)
```

**Detektor + alarm na pasmie anomalii:**

```bash
# 1. Utworzenie modelu anomalii (zaczyna się uczyć od razu na historii do 2 tygodni)
aws cloudwatch put-anomaly-detector --single-metric-anomaly-detector '{
  "Namespace": "ContainerInsights",
  "MetricName": "pod_cpu_utilization",
  "Dimensions": [
    {"Name": "ClusterName", "Value": "lab-eks"},
    {"Name": "Namespace",   "Value": "shop"},
    {"Name": "PodName",     "Value": "cart"}
  ],
  "Stat": "Average"
}'

# 2. Alarm: wartość powyżej górnej granicy pasma (2 odchylenia standardowe), 3 z 5 okresów
aws cloudwatch put-metric-alarm \
  --alarm-name "shop-cart-cpu-anomaly" \
  --comparison-operator GreaterThanUpperThreshold \
  --evaluation-periods 5 --datapoints-to-alarm 3 \
  --threshold-metric-id ad1 \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:eu-central-1:123456789012:lab-alerts \
  --metrics '[
    {"Id": "m1", "ReturnData": true,
     "MetricStat": {"Metric": {"Namespace": "ContainerInsights", "MetricName": "pod_cpu_utilization",
       "Dimensions": [{"Name": "ClusterName","Value": "lab-eks"},{"Name": "Namespace","Value": "shop"},{"Name": "PodName","Value": "cart"}]},
       "Period": 300, "Stat": "Average"}},
    {"Id": "ad1", "Expression": "ANOMALY_DETECTION_BAND(m1, 2)", "Label": "CPU (expected)", "ReturnData": true}
  ]'

# 3. Wykluczenie okresu awarii z treningu modelu
aws cloudwatch put-anomaly-detector --single-metric-anomaly-detector '{...jak wyżej...}' \
  --configuration '{"ExcludedTimeRanges":[{"StartTime":"2026-10-01T10:00:00Z","EndTime":"2026-10-01T12:00:00Z"}]}'
```

**Terraform (fragment):**

```hcl
resource "aws_cloudwatch_metric_alarm" "cart_cpu_anomaly" {
  alarm_name          = "shop-cart-cpu-anomaly"
  comparison_operator = "GreaterThanUpperThreshold"
  evaluation_periods  = 5
  datapoints_to_alarm = 3
  threshold_metric_id = "ad1"
  alarm_actions       = [aws_sns_topic.lab_alerts.arn]

  metric_query {
    id          = "ad1"
    expression  = "ANOMALY_DETECTION_BAND(m1, 2)"
    label       = "CPU (expected)"
    return_data = true
  }

  metric_query {
    id          = "m1"
    return_data = true
    metric {
      namespace   = "ContainerInsights"
      metric_name = "pod_cpu_utilization"
      period      = 300
      stat        = "Average"
      dimensions  = { ClusterName = "lab-eks", Namespace = "shop", PodName = "cart" }
    }
  }
}
```

W konsoli: *CloudWatch → Metrics → wybierz metrykę → Graphed metrics → ikona „pulsu” (Pretty anomaly detection)*. Pasmo pojawia się na wykresie, a z tego miejsca można utworzyć alarm.

### 6.2 AWS: CloudWatch Logs Anomaly Detection

```bash
# Detektor na grupie logów aplikacji z EKS (Container Insights / Fluent Bit)
aws logs create-log-anomaly-detector \
  --detector-name shop-app-logs \
  --log-group-arn-list "arn:aws:logs:eu-central-1:123456789012:log-group:/aws/containerinsights/lab-eks/application" \
  --evaluation-frequency FIFTEEN_MIN \
  --anomaly-visibility-time 14

# Lista wykrytych anomalii
aws logs list-anomalies --anomaly-detector-arn <ARN-z-poprzedniej-komendy>
```

Ad hoc w **Logs Insights**:

```
fields @timestamp, @message
| filter @message like /(?i)error|exception/
| pattern @message
| anomaly
```

Alarm na anomaliach logów: metryka `AnomalyCount` w przestrzeni `AWS/Logs` (wymiar `LogAnomalyDetector` / priorytet).

### 6.3 AWS: CloudWatch investigations

1. *CloudWatch → AI Operations → Investigations → Configure* (jednorazowo na konto). Tworzy *investigation group* i rolę IAM (wybierz polityki read-only: `AIOpsAssistantPolicy`). Dodaj źródła: CloudTrail, X-Ray, EKS access entry.
2. Start dochodzenia:
   - z alarmu: *Alarm → Investigate*,
   - z wykresu metryki: *Investigate*,
   - z wyniku Logs Insights,
   - automatycznie: akcja alarmu „Start investigation”.
3. Przejrzyj **observations** i **hypotheses**, akceptuj lub odrzucaj sugestie, na końcu wygeneruj raport z incydentu.

```bash
# Alarm, który automatycznie uruchamia dochodzenie (akcja alarmu = investigation group)
aws cloudwatch put-metric-alarm ... \
  --alarm-actions "arn:aws:aiops:eu-central-1:123456789012:investigation-group/<ID>"
```

> Sprawdź dostępność CloudWatch investigations w regionie labu (np. `eu-central-1`) oraz to, czy wnioskowanie LLM odbywa się w regionie, czy przez *cross-region inference*.

### 6.4 Grafana ML z danymi z AWS

Grafana ML działa **tylko w Grafana Cloud** (nie w Amazon Managed Grafana ani w OSS). Na środowisku AWS masz dwie drogi:

**A. Wysyłka metryk z EKS do Grafana Cloud (zalecane na lab):**

```bash
# Grafana Cloud → Connections → Kubernetes Monitoring → wygeneruje gotową komendę Helm z tokenami
helm repo add grafana https://grafana.github.io/helm-charts
helm upgrade --install grafana-k8s-monitoring grafana/k8s-monitoring \
  -n monitoring --create-namespace -f values-from-grafana-cloud.yaml
```

**B. Podpięcie istniejącego źródła:** Prometheus (self-hosted w EKS, wystawiony bezpiecznie) albo Amazon Managed Service for Prometheus (Prometheus data source z SigV4). Upewnij się, że dane źródło jest na liście wspieranych przez Grafana ML. CloudWatch na niej nie ma.

**Forecast (UI):** *Machine Learning → Metric forecasts → New forecast*:
1. Źródło danych i zapytanie, np. `sum(rate(http_requests_total{namespace="shop"}[5m]))`.
2. Zakres treningu (np. 30 dni), interwał, sezonowość, przedział ufności (np. 95%).
3. Zapis. Model trenuje się i odświeża cyklicznie.
4. *Create alert* z prognozy, czyli reguła „wartość poza pasmem przez X minut”. Prognozę można też dodać jako panel na dashboardzie.

**Outlier detector:** *Machine Learning → Outlier detection → New*. Zapytanie zwracające grupę serii, np. `histogram_quantile(0.95, sum by (pod, le) (rate(http_request_duration_seconds_bucket{app="cart"}[5m])))`, algorytm DBSCAN/MAD, czułość. Potem alert na „pod jest outlierem”.

**Sift:** z alertu lub panelu *Run Sift investigation*, albo *Machine Learning → Sift → New investigation* z wybranym klastrem, namespace'em i zakresem czasu.

### 6.5 Azure Monitor (przykład do porównania)

```bash
# Alert metryczny z dynamicznym progiem: CPU VM, czułość średnia, 2 naruszenia z 4 okresów
az monitor metrics alert create \
  -n vm-cpu-dynamic -g rg-lab \
  --scopes /subscriptions/<sub>/resourceGroups/rg-lab/providers/Microsoft.Compute/virtualMachines/vm-app \
  --condition "avg Percentage CPU > dynamic medium 2 of 4" \
  --window-size 5m --evaluation-frequency 5m \
  --action /subscriptions/<sub>/resourceGroups/rg-lab/providers/microsoft.insights/actionGroups/ag-lab
```

```kusto
// Wykrywanie anomalii w KQL (Log Analytics): liczba błędów 5xx na 5 min
AppRequests
| where TimeGenerated > ago(7d)
| make-series failures = countif(toint(ResultCode) >= 500) default=0 on TimeGenerated step 5m
| extend (anomalies, score, baseline) = series_decompose_anomalies(failures, 2.5)
| render anomalychart with (anomalycolumns=anomalies)
```

### 6.6 Bonus: wykrywanie anomalii za darmo w samym Prometheusie

Gdy firma nie chce Grafana Cloud ani CloudWatch AD, Grafana Labs udostępnia open-source'owy framework *PromQL anomaly detection* (recording rules z pasmem opartym na średniej i odchyleniu standardowym oraz sezonowości). Najprostsza wersja z-score:

```yaml
groups:
  - name: anomaly
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
      - alert: RequestRateAnomaly
        expr: |
          abs(
            job:http_requests:rate5m
            - avg_over_time(job:http_requests:rate5m[1d] offset 1w)
          ) / stddev_over_time(job:http_requests:rate5m[1d] offset 1w) > 3
        for: 10m
```

To dobry materiał edukacyjny, bo pokazuje, że „ML-owe” pasmo to w dużej mierze statystyka.

---

## Źródła

**Azure**
- Dynamic thresholds: https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-dynamic-thresholds
- Wycofanie Anomaly Detector: https://learn.microsoft.com/en-us/azure/ai-services/anomaly-detector/overview
- Cennik Azure Monitor: https://azure.microsoft.com/en-us/pricing/details/monitor/

**Grafana**
- Grafana ML: https://grafana.com/docs/grafana-cloud/ai-tools/machine-learning/
- Koszty i limity Grafana ML: https://grafana.com/docs/grafana-cloud/machine-learning/billing/
- Outlier detection: https://grafana.com/blog/introducing-outlier-detection-in-grafana-machine-learning-for-grafana-cloud/

**AWS**
- CloudWatch anomaly detection: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html
- Logs anomaly detection: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection-Enable.html
- CloudWatch investigations: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Investigations.html
- Koszty investigations: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/investigations-costs.html
- Wygaszenie DevOps Guru (09.2026): https://aws.amazon.com/about-aws/whats-new/2026/09/aws-service-availability/
- Wyłączenie Lookout for Metrics: https://aws.amazon.com/blogs/machine-learning/transitioning-off-amazon-lookout-for-metrics/
- Cennik CloudWatch: https://aws.amazon.com/cloudwatch/pricing/
