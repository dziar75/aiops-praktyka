# Robusta i HolmesGPT — alerty z kontekstem i agent śledczy

Materiał pomocniczy do Dnia 1, temat 1.4.4. Diagram architektury: [`architektura.html`](architektura.html). Poprzednie narzędzie z tego tematu: [`../03-k8sgpt/k8sgpt.md`](../03-k8sgpt/k8sgpt.md).

> Stan na październik 2026. Wersje i funkcje zmieniają się szybko, więc w razie wątpliwości sprawdź README obu projektów.
>

---

## TL;DR

| | **Robusta** | **HolmesGPT** |
|---|---|---|
| **Jednym zdaniem** | Silnik obsługi zdarzeń: dokłada do alertów kontekst, wykonuje akcje i wysyła bogate powiadomienia | Agent AI, który bada alert albo pytanie i pisze hipotezę przyczyny z dowodami |
| **Wyzwalacz** | Alert z Alertmanagera albo zdarzenie w klastrze | Alert (przez Robustę) albo pytanie w CLI (`holmes ask`) |
| **Gdzie działa** | Helm chart w klastrze (runner + forwarder) | W klastrze razem z Robustą albo jako CLI na laptopie |
| **Logika** | Reguły (playbooki), deterministyczne | LLM w pętli z narzędziami, niedeterministyczne |
| **Wynik** | Wzbogacony alert w Slacku/Teams/PagerDuty… | Hipoteza + dowody + sugerowany następny krok |
| **Licencja** | Rdzeń MIT; UI jako SaaS (platform.robusta.dev) | Apache 2.0, CNCF Sandbox |
| **Popularność (GitHub)** | ~3,1k ★ | osobne repo |

---

## 1. Jak działa Robusta

### Komponenty

- **Runner**: główny proces w Pythonie, który wykonuje playbooki.
- **Forwarder**: obserwuje API Kubernetesa (zmiany zasobów, eventy) i przekazuje je do runnera.
- **Sinki**: miejsca docelowe wiadomości. Ponad 25: Slack, MS Teams, Discord, PagerDuty, Opsgenie, Jira, ServiceNow, e-mail, webhook, Kafka.
- **Robusta UI** (opcjonalnie, SaaS): oś czasu zdarzeń, widok klastra, część funkcji AI. Tu wchodzi model open-core.
- Opcjonalnie wbudowany **kube-prometheus-stack**, jeśli nie masz własnego Prometheusa. My mamy własny.

### Playbooki: trigger → akcje → sink

```yaml
customPlaybooks:
  - triggers:
      - on_prometheus_alert:
          alert_name: KubePodCrashLooping
    actions:
      - logs_enricher: {}          # dołącz logi poda
      - pod_events_enricher: {}    # dołącz eventy
    sinks:
      - main_slack_sink
```

**Triggery są dwóch rodzajów** (ważne rozróżnienie):
1. **Alerty z Prometheusa** (`on_prometheus_alert`): Robusta dostaje webhook z Alertmanagera.
2. **Zdarzenia w Kubernetesie, bez Prometheusa:** crash loop, OOMKill, nieudany Job, zmiana Deploymentu, eventy typu Warning. Robusta widzi je sama przez forwarder.

Robusta nie jest więc tylko „dodatkiem do Alertmanagera”. Po instalacji ma **gotowe playbooki** dla typowych awarii (crash loop, OOMKill, ImagePullBackOff, nieudany Job, node NotReady), które działają od razu. Na tym polu częściowo pokrywa się z k8sgpt, tyle że reaguje w momencie zdarzenia, a nie przy skanie.

**Akcje:**
- **Enrichery** (dokładanie kontekstu): logi, także z poprzedniego kontenera; eventy; wykres CPU i pamięci z Prometheusa; diff ostatniej zmiany w Deploymencie; informacje o node'zie.
- **Akcje naprawcze**: np. usunięcie poda, zebranie zrzutu wątków. To początek auto-remediacji i wymaga szerszego RBAC.
- **Własne akcje** w Pythonie.

**Grupowanie i routing:** ten sam alert z wielu podów idzie jako jedna wiadomość; routing według namespace'u, zespołu czy severity.

### Co widzi człowiek na dyżurze

Bez Robusty alert z Alertmanagera to zwykle jedna linijka: `KantynaHighErrorRate firing`. Potem 5–6 komend `kubectl`.

Z Robustą ta sama wiadomość przychodzi z załącznikami:
- ostatnie linie logu ze stack trace'em,
- eventy poda,
- wykres błędów albo pamięci z ostatniej godziny,
- „20 minut temu zmieniono obraz z 1.0.0 na 1.1.0”.

To jest główna wartość Robusty i działa **bez AI**.

---

## 2. HolmesGPT: warstwa AI

**HolmesGPT** to osobny projekt, który wyrósł z Robusty. Dziś jest w CNCF Sandbox, a Microsoft pomaga go rozwijać. Działa samodzielnie jako CLI (`holmes ask …`) albo w integracji z Robustą.

Holmes jest **agentem**, czym fundamentalnie różni się od k8sgpt:

```
alert ──▶ Holmes ──▶ LLM: "co sprawdzić?"
                      LLM: "kubectl describe pod …"          ──▶ wynik
                      LLM: "zapytanie do Prometheusa"        ──▶ wynik
                      LLM: "logi z Loki z ostatnich 30 min"  ──▶ wynik
                      … pętla …
          ◀── hipoteza przyczyny + dowody + sugerowany krok
```

- **Toolsety**: zestawy narzędzi, z których Holmes korzysta: Kubernetes, Prometheus, Loki, Grafana, Datadog, AWS, bazy danych i inne. Deklaratywnie tylko do odczytu; zakres ograniczasz w konfiguracji.
- **Runbooki**: można mu podać własne instrukcje typu „przy tym alercie sprawdź najpierw X”. Łączy się z tematem 3.3.
- **Model**: Holmes wewnętrznie używa **biblioteki** LiteLLM, więc łatwo podpiąć go do naszego proxy. Potrzebuje dobrego modelu z wywoływaniem narzędzi.
- **Koszt**: jeden incydent to wiele wywołań LLM. Przy hałaśliwym alertingu rachunek rośnie szybko.
- **W Robuście**: przycisk „Ask Holmes” pod alertem w Slacku; wynik wraca jako nowa wiadomość. **Sprawdzone 3.10 na Robuście 0.50.0: bez Robusta UI (SaaS) przycisk nie działa**, mimo że jedna z wersji dokumentacji Robusty twierdzi inaczej. Kliknięcia wracają do runnera przez przekaźnik Robusty (relay), a runner tworzy to połączenie tylko wtedy, gdy skonfigurowany jest sink Robusta UI (log: „No robusta sinks found, skipping receiver creation”). Do tego przyciski działają tylko z oficjalną aplikacją Robusty w Slacku, nie z własną. Bez UI zostaje akcja `ask_holmes` w playbooku, ale przyjmuje tylko stałe parametry, a nie treść konkretnego alertu. Własny model (u nas LiteLLM) nie wymaga konta Robusty.

### Czy Holmes może coś zmienić w klastrze?

Sprawdzone 3.10 w kodzie HolmesGPT 0.42.0 (toolset `bash`, `holmes/plugins/toolsets/bash/`).

**Domyślnie: tylko odczyt i podpowiedzi.** Narzędzie `bash` ma wbudowaną listę komend dozwolonych bez pytania (`builtin_allowlist: core`). Są na niej wyłącznie komendy tylko do odczytu: `kubectl get/describe/logs/top/events/diff/auth can-i`, `jq`, `grep`, `head`, `tail`… Nie ma na niej `delete`, `rollout restart`, `scale`, `apply`, `patch` ani `edit`.

Gdy model chce uruchomić komendę spoza listy:

| Tryb | Co się dzieje |
|---|---|
| CLI interaktywne (domyślne) | Holmes **pyta o zgodę**; po zgodzie wykonuje komendę Twoim kubeconfigiem |
| `--bash-always-deny` | Odrzuca bez pytania, więc Holmes tylko podpowiada |
| `--bash-always-allow` | **Wykonuje bez pytania**; dokumentacja zaleca to tylko w izolowanym środowisku (sandbox) |
| Konfiguracja `toolsets.bash.config.allow: ["kubectl delete", …]` | Wskazane komendy przestają wymagać zgody |
| Własne toolsety (YAML, `-t`) | Można dać agentowi gotowe narzędzie, np. „restart_deployment” |

Drugie narzędzie, `kubectl-run`, uruchamia tymczasowego poda (np. z `curl`), ale tylko z obrazów z listy `allowed_images`. U nas lista jest pusta, więc 3.10 Holmes dostał odmowę.

**Czysto teoretycznie, po takiej konfiguracji Holmes może skasować Deployment, PVC i cokolwiek innego**, na co pozwala konto, którym działa. Dlatego:
- **Twarda granica to RBAC, nie lista w Holmesie.** Lista `allow`/`deny` działa na dopasowaniu prefiksu komendy. To mechanizm wygody, a nie zabezpieczenie, zwłaszcza wobec agenta zmanipulowanego przez prompt injection w logu (wrócimy do tego w dniu 3).
- Holmes na **kubeconfigu admina** (CLI na laptopie) to „junior z kluczami do serwerowni”. Holmes w klastrze (Robusta, osobny chart) działa na **ServiceAccount tylko do odczytu**, więc nawet zatwierdzona komenda zapisu skończy się `Forbidden`.
- Jeśli agent ma naprawiać: rola z minimalnym zapisem (np. tylko `patch` na `deployments` w jednym namespace, bez `delete`, PVC i Secretów), wąskie narzędzia zamiast ogólnego `bash`, `deny` na groźne komendy jako druga warstwa, zgoda człowieka, polityki Kyverno/admission blokujące usuwanie chronionych zasobów, audyt EKS.
- Robusta ma **własne akcje naprawcze** w playbookach (np. usunięcie poda). To reguły zdefiniowane z góry przez człowieka, a nie decyzja AI.

Na szkoleniu łączy się to z zasadą „AI jako junior do weryfikacji” (1.1.5), uprawnieniami asystentów (1.2.3: `--bash-always-allow` ≈ `--dangerously-skip-permissions` w Claude Code) i labem dnia 3 („agent proponuje akcję, człowiek zatwierdza”).

---

## 3. Robusta a k8sgpt

| | k8sgpt | Robusta (bez AI) | HolmesGPT |
|---|---|---|---|
| **Wyzwalacz** | skan (Ty albo operator) — *pull* | **zdarzenie**: alert, crash, deploy — *push* | alert albo pytanie |
| **Źródła** | stan obiektów K8s | alerty + eventy + logi + metryki + historia zmian | wszystko z toolsetów |
| **Logika** | reguły | reguły (playbooki) | **LLM w pętli** |
| **Rola AI** | tłumacz gotowego błędu | — | agent śledczy |
| **Deterministyczne** | tak (wykrywanie) | tak | nie |
| **Wynik** | lista problemów | wzbogacony alert w kanale | hipoteza z dowodami |
| **Zmienia klaster** | nie | tak (akcje w playbookach) | domyślnie nie; w CLI za zgodą człowieka (`bash`), granicą jest RBAC konta |
| **Czego nie widzi** | metryk, logów, problemów przy zielonych podach | problemów bez alertu ani reguły | tego, do czego nie ma toolsetu |
| **Próg wejścia** | bardzo niski: `brew install` + komenda | średni: Helm, sinki, najlepiej istniejący Prometheus | jak Robusta + dobry model |
| **Najlepsze dla** | triage, nauka, CI | zespoły SRE z dojrzałym alertingiem | dochodzenie przy incydencie |

**W jednym zdaniu:** k8sgpt mówi „co jest zepsute”, Robusta mówi „oto alert razem ze wszystkim, czego potrzebujesz, żeby zacząć”, a Holmes mówi „myślę, że to dlatego, a oto dowody”. Narzędzia się uzupełniają: k8sgpt na triage, Robusta na on-call.

---

## 4. Jaką ma opinię?

**Plusy:**
- Realnie **zmniejsza szum** i skraca MTTR. Alert z logami i wykresem w Slacku oszczędza kilka kroków `kubectl`.
- Dobrze współpracuje z istniejącym kube-prometheus-stack i nie wymaga przebudowy monitoringu.
- HolmesGPT to jeden z najbardziej dojrzałych open-source'owych agentów SRE. Wejście do CNCF i wsparcie Microsoftu zwiększają zaufanie do projektu.

**Minusy:**
- Model biznesowy **open-core**: najwygodniejsze funkcje (UI, timeline, część AI) działają w SaaS Robusty, co dla wielu firm oznacza problem z compliance.
- Konfiguracja playbooków w YAML-u bywa nieintuicyjna, a dokumentacja nie nadąża za zmianami.
- Wartość rośnie wraz z jakością alertingu. Przy słabych regułach Prometheusa Robusta niewiele poprawi.
- Koszt tokenów przy dużej liczbie alertów analizowanych przez Holmesa.

**Ogólny werdykt:** dobry wybór dla zespołów, które mają już Prometheusa i chcą lepszego on-calla. Przy małych klastrach to zwykle przerost formy nad treścią.

---

## 5. Czy jest bezpieczna?

Ryzyka wspólne dla narzędzi AI w diagnostyce Kubernetesa (wyciek do LLM, uprawnienia, prompt injection, halucynacje, klucze) i checklista przed wdrożeniem: [`../03-k8sgpt/k8sgpt.md`](../03-k8sgpt/k8sgpt.md), sekcja 5. Specyfika Robusty i Holmesa:

- **Runner ma szeroki RBAC**: odczyt większości zasobów, a dla akcji naprawczych także zapis (restart, usuwanie podów). **Przejrzyj `values.yaml` i ClusterRole przed instalacją.**
- **Logi w Slacku to wyciek poza klaster.** Jeśli w logu są tokeny albo dane klientów, właśnie trafiły do kanału, który czyta pół firmy.
- **SaaS**: domyślna konfiguracja z UI wysyła metadane klastra, alerty i enrichment do platform.robusta.dev. Alternatywy: tryb bez UI (dane tylko do Twoich sinków) albo self-hosted (oferta komercyjna). Przy SaaS: DPA.
- **HolmesGPT** deklaruje działanie **read-only z poszanowaniem RBAC**, ale wszystko, co odczyta, trafia do LLM-a. Prompt injection w logach to realne ryzyko dla agenta (temat dnia 3). W CLI komendy zapisu są możliwe po zgodzie albo po zmianie konfiguracji (sekcja 2), więc **nie uruchamiaj Holmesa na kubeconfigu admina produkcji**.
- **Model**: własny endpoint (Azure OpenAI, Bedrock, Vertex, LiteLLM, Ollama) jest możliwy, ale agent potrzebuje dobrego modelu z tool callingiem.

Dodatkowe punkty checklisty dla Robusty:
- [ ] Czy dane trafiają do SaaS Robusty? Jeśli tak, czy jest DPA?
- [ ] Które playbooki mają akcje zapisujące i kto je zatwierdził?
- [ ] Zakres toolsetów Holmesa ograniczony do potrzebnych?
- [ ] Holmes działa na koncie tylko do odczytu? Nikt nie używa `--bash-always-allow` ani szerokiego `allow` poza sandboxem?
- [ ] Kto ma dostęp do kanału, do którego trafiają logi z alertów?

---

## 6. Instalacja i użycie

### 6.1 Robusta

**Wymagania:** klaster K8s, Helm 3, Python 3 + pip (do generatora configu), opcjonalnie istniejący Prometheus.

**Krok 1: wygenerowanie konfiguracji:**

```bash
pip install -U robusta-cli --no-cache
robusta gen-config
# Kreator zapyta m.in. o:
#  - sink (Slack / MS Teams / ...),
#  - czy zainstalować wbudowany Prometheus → u nas "nie" (mamy kube-prometheus-stack),
#  - czy włączyć Robusta UI (SaaS) → "nie", jeśli dane nie mogą wyjść do SaaS
# Wynik: generated_values.yaml
```

**Krok 2: instalacja Helmem:**

```bash
helm repo add robusta https://robusta-charts.storage.googleapis.com
helm repo update
helm install robusta robusta/robusta \
  -f ./generated_values.yaml \
  --set clusterName=szkolenie-lab \
  -n robusta --create-namespace

kubectl get pods -n robusta
```

**Krok 3: podpięcie istniejącego Alertmanagera** (webhook do Robusty):

```yaml
receivers:
  - name: 'robusta'
    webhook_configs:
      - url: 'http://robusta-runner.robusta.svc.cluster.local/api/alerts'
        send_resolved: true
route:
  routes:
    - receiver: 'robusta'
      matchers: [ 'severity =~ ".*"' ]
      continue: true
```

**Krok 4: HolmesGPT** w `generated_values.yaml`. Na szkoleniu przez LiteLLM w klastrze (format modelu LiteLLM `openai/…` + adres bramy):

```yaml
enableHolmesGPT: true
holmes:
  additionalEnvVars:
    - name: MODEL
      value: openai/claude-sonnet-5-5                  # nazwa modelu z naszej bramy
    - name: OPENAI_API_BASE
      value: http://litellm.ai:4000/v1                 # LiteLLM w klastrze
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: holmes-secrets
          key: litellm-key
```

```bash
kubectl create secret generic holmes-secrets -n robusta \
  --from-literal=litellm-key=<klucz-LiteLLM>
helm upgrade robusta robusta/robusta -f generated_values.yaml -n robusta \
  --set clusterName=szkolenie-lab
```

⚠️ Nazwy zmiennych (`OPENAI_API_BASE` vs `OPENAI_BASE_URL`) i format modelu sprawdź w dokumentacji HolmesGPT przy instalacji. Alternatywa bez bramy: `MODEL=anthropic/claude-sonnet-5-5` + `ANTHROPIC_API_KEY`.

**Test działania:**

```bash
# Testowy alert bez czekania na Prometheusa
robusta playbooks trigger prometheus_alert alert_name=KubePodCrashLooping \
  namespace=default pod_name=<nazwa-poda>

# Albo celowy crash
kubectl run crasher --image=busybox -- sh -c "exit 1"
```

### 6.2 HolmesGPT jako samodzielne CLI

```bash
brew tap robusta-dev/homebrew-holmesgpt
brew install holmesgpt
# lub: pipx install holmesgpt

export OPENAI_API_BASE=https://llm.aiops.marniok.dev/v1
export OPENAI_API_KEY=<klucz-LiteLLM>
holmes ask "dlaczego orders-api w namespace demo zwraca błędy 500?" \
  --model openai/claude-sonnet-5-5

# Analiza aktywnych alertów z Alertmanagera
holmes investigate alertmanager --alertmanager-url http://localhost:9093
```

Holmes sam uruchamia `kubectl get/describe/logs`, odpytuje Prometheusa itd., a na końcu przedstawia hipotezę wraz z dowodami.


---

## Źródła

- Robusta: https://github.com/robusta-dev/robusta · https://docs.robusta.dev
- HolmesGPT: https://github.com/robusta-dev/holmesgpt
