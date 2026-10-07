# Grafana AI i Elastic AI — asystenci AI w platformach observability

Materiał pomocniczy do szkolenia „AIOps w praktyce”. Diagram architektury: [`architektura.html`](architektura.html).

> Stan na październik 2026. W obu produktach AI zmienia się z wydania na wydanie, a cenniki co kilka miesięcy. **Sprawdź linki w sekcji Źródła, zanim z nich skorzystasz.**

---

## TL;DR

| | **Grafana Assistant** (Grafana AI) | **Elastic AI Agent / AI Assistant** |
|---|---|---|
| **Jednym zdaniem** | Agent AI wbudowany w Grafanę: pisze PromQL/LogQL, buduje dashboardy, prowadzi dochodzenia | Czat AI w Kibanie: odpytuje dane w Elasticsearch (ES\|QL), analizuje alerty, logi i APM |
| **Gdzie działa backend AI** | Zawsze w **Grafana Cloud**, także przy Grafanie self-hosted | W Kibanie (Twoja instancja), LLM dowolny przez konektor |
| **Wybór modelu** | Nie: modelem zarządza Grafana Labs | Tak: OpenAI, Azure OpenAI, Bedrock, Gemini, lokalny (LM Studio / OpenAI-compatible) albo Elastic Managed LLM |
| **Darmowo?** | **Tak**: Grafana Cloud Free daje 3 aktywnych użytkowników AI miesięcznie | **Nie**: wymaga subskrypcji **Enterprise** (self-managed / Cloud Hosted) albo odpowiedniego tieru Serverless. Do nauki wystarczy trial |
| **Zmiana w 2026** | Assistant GA (styczeń 2026), dostępny też on-prem przez połączenie z Cloud (kwiecień 2026), preinstalowany w Grafana Enterprise 13.1 | Od Elastic 9.4 domyślnym czatem jest **AI Agent (Agent Builder)**, a stary AI Assistant jest *deprecated* |

**Odpowiedź na pytanie o licencje:**
- **Grafana:** na szkolenie **nie potrzebujesz płatnej licencji.** W labie 05 używasz wspólnej Grafany szkolenia; własne darmowe konto Grafana Cloud założysz po szkoleniu. Przy samodzielnie hostowanej Grafanie OSS też da się użyć Assistanta, ale tylko przez połączenie z (darmowym) stackiem Grafana Cloud.
- **Elastic:** produkcyjnie **potrzebujesz Enterprise**. Na szkolenie wystarczy **darmowy trial**: 14 dni w Elastic Cloud albo 30 dni na self-managed. Klucz do LLM opłacasz osobno, chyba że korzystasz z Elastic Managed LLM w ramach triala Cloud.

---

## 1. Do czego służą?

### Grafana Assistant (i reszta „Grafana AI”)

Grafana Assistant to agent AI w panelu bocznym Grafany, który zna Twoje źródła danych (Prometheus/Mimir, Loki, Tempo, Pyroscope, a także inne datasource'y) i potrafi w nich działać:

- **Tworzenie zapytań językiem naturalnym:** „pokaż p95 latencji dla serwisu checkout z ostatniej godziny” zamienia na PromQL/LogQL/TraceQL, wykonuje zapytanie i tłumaczy wynik.
- **Budowanie i edycja dashboardów:** generuje panele, poprawia istniejące, opisuje, co pokazuje dashboard.
- **„Explain in Assistant”:** wyjaśnianie paneli, błędów w logach i alertów jednym kliknięciem.
- **Assistant Investigations:** wieloagentowe dochodzenie w sprawie incydentu. Agent przegląda metryki, logi i trace'y, buduje hipotezy i raport z przyczyną. Może startować automatycznie z alertu lub incydentu.
- **Integracje:** Slack, MS Teams, CLI i serwer MCP, więc Assistanta można wołać spoza UI.
- **Watchers / Automations:** ciągłe obserwowanie sygnałów przez agenta (preview).

Inne funkcje AI/ML w ekosystemie Grafany (warto znać nazwy):
- **Sift:** automatyczna diagnostyka (wykrywanie anomalii, korelacja z deployami, „noisy neighbours”) w Grafana Cloud.
- **Adaptive Metrics / Adaptive Logs:** ML, który tnie nieużywaną telemetrię i obniża koszty.
- **Grafana LLM plugin (`grafana-llm-app`):** open-source'owa „wtyczka do LLM” dla Grafany OSS/Enterprise. Działa z Twoim kluczem API. Daje drobne funkcje (generowanie tytułów i opisów paneli, wyjaśnianie) i jest fundamentem dla innych pluginów. **To nie jest Assistant.**
- **mcp-grafana:** open-source'owy serwer MCP (Apache 2.0), który pozwala Claude Code, Cursorowi i innym asystentom odpytywać Grafanę, Prometheusa i Loki. To darmowa alternatywa dla Assistanta.

### Elastic AI (AI Agent / AI Assistant)

Elastic ma kilka „twarzy” AI, ale w kontekście observability chodzi o czat w Kibanie:

- **Elastic AI Agent (Agent Builder):** od 9.4 domyślny czat w widokach Observability, Security i Search. Agent z *skills* (np. `observability.investigation`), narzędziami i możliwością tworzenia własnych agentów. Integruje się z Elastic Workflows.
- **AI Assistant for Observability and Search:** starszy czat, od 9.4 *deprecated*, ale nadal dostępny po przełączeniu w *GenAI Settings*. Ma funkcje, których Agent Builder jeszcze nie ma: **Knowledge Base**, **anonimizację**, udostępnianie czatów, pełny audit log i cytowania.
- **Contextual insights:** przyciski „wyjaśnij” przy logach, błędach APM, alertach i hostach w Infrastructure.
- **Funkcje (tool calling):** generowanie i wykonywanie zapytań **ES|QL**, pobieranie alertów, wykrywanie *change points*, tworzenie wizualizacji, przeszukiwanie Knowledge Base (runbooki, dokumentacja z GitHuba, Confluence, Jira).
- **Konektor AI w regułach alertów:** gdy alert odpali, kontekst trafia do asystenta, a analiza idzie dalej do Slacka, e-maila, Jiry lub PagerDuty.
- **AI Assistant for Security / Attack Discovery:** odpowiednik dla SIEM. Analizuje alerty bezpieczeństwa i łączy je w scenariusze ataków. Poza zakresem tego materiału, ale ma ten sam model licencyjny.

---

## 2. Czym się różnią?

| Wymiar | Grafana Assistant | Elastic AI Agent / Assistant |
|---|---|---|
| **Filozofia** | „Big tent”: wiele źródeł danych (Prometheus, Loki, Tempo, SQL, chmury) | Wszystko w Elasticsearch: jeden silnik, jeden język zapytań (ES\|QL) |
| **Języki zapytań** | PromQL, LogQL, TraceQL, SQL… | ES\|QL (plus KQL/Query DSL) |
| **Gdzie przetwarzany jest prompt** | Backend Grafana Cloud (zawsze SaaS) | Twoja Kibana + wybrany przez Ciebie dostawca LLM |
| **Kontrola nad modelem** | Brak. Model dobiera Grafana Labs | Pełna: własny konektor, nawet lokalny model |
| **Działanie offline / air-gapped** | **Niemożliwe** (Assistant wymaga połączenia z Cloud) | **Możliwe** z lokalnym LLM (np. LM Studio, vLLM, Ollama przez OpenAI-compatible API) |
| **Baza wiedzy (runbooki)** | Kontekst z Grafany (dashboardy, alerty, opisy) + instrukcje/reguły | Knowledge Base na ELSER/E5 z konektorami (GitHub, Confluence, Jira); w Agent Builder na razie brak |
| **Automatyczne dochodzenia** | Assistant Investigations (z alertu/incydentu) | Konektor AI w regułach alertów + skill `observability.investigation` |
| **Model rozliczeń** | Per aktywny użytkownik AI + tokeny | Subskrypcja Enterprise (lub tier Serverless) + koszt LLM (Twój lub Elastic Managed LLM) |
| **Próg wejścia** | Bardzo niski: konto Cloud i od razu działa | Średni: konektor LLM, uprawnienia, licencja/trial, opcjonalnie węzeł ML pod KB |
| **Najlepsze dla** | Zespoły na stacku Prometheus/Loki/Tempo, Grafana Cloud | Zespoły, które trzymają logi/APM/SIEM w Elasticu |

**Najkrócej:** Grafana Assistant to wygodny SaaS, który działa od razu, ale wymaga oddania promptów do chmury Grafany. Elastic daje kontrolę nad modelem i danymi, ale za AI trzeba zapłacić najwyższy tier subskrypcji.

---

## 3. Jaką mają opinię?

### Grafana Assistant

**Plusy:**
- Najczęściej chwalona rzecz: **generowanie PromQL/LogQL**. Dla osób, które nie pamiętają składni `histogram_quantile` czy `rate()`, to realne przyspieszenie pracy.
- Szybkie tworzenie dashboardów „z opisu” i wyjaśnianie cudzych dashboardów przy przejmowaniu systemu.
- Hojny darmowy tier (40M tokenów na użytkownika) wystarcza na naukę i małe zespoły.
- Investigations dobrze oceniane przy prostych incydentach (deploy → wzrost błędów → konkretny pod).

**Minusy:**
- **Zależność od Grafana Cloud**, także przy Grafanie self-hosted. Dla wielu firm (sektor publiczny, finanse, air-gap) to wyklucza narzędzie.
- Brak wyboru modelu i niewielka przejrzystość, co dokładnie trafia do backendu.
- Rozliczanie per aktywny użytkownik: wystarczy jedno kliknięcie „Explain in Assistant”, żeby ktoś liczył się jako aktywny. Trudno przewidzieć koszty w dużych organizacjach.
- Jak każdy LLM: bywają błędne zapytania (złe etykiety, nieistniejące metryki). Zawsze trzeba sprawdzić wynik.
- Szybkie zmiany nazw i funkcji (LLM plugin → Assistant → Investigations → Watchers), więc dokumentacja i tutoriale szybko się dezaktualizują.

### Elastic AI

**Plusy:**
- **Wolny wybór LLM**, w tym lokalnego, co jest dużym atutem w środowiskach regulowanych.
- **ES|QL** okazał się dobrym językiem dla LLM-ów: modele generują go poprawniej niż złożony Query DSL.
- Knowledge Base z runbookami daje odpowiedzi „po firmowemu”, a nie ogólne porady.
- Spójne AI dla observability i security w jednym produkcie.

**Minusy:**
- **Bariera licencyjna:** AI tylko w Enterprise. Najczęstsza skarga na forach: „żeby spróbować AI, muszę kupić najwyższy plan”.
- **Zamieszanie produktowe w 2026:** AI Assistant zastąpiony przez AI Agent (Agent Builder), który nie ma jeszcze części funkcji (Knowledge Base, anonimizacja). Dwa różne API i historie czatów nie przenoszą się między nimi.
- Konfiguracja jest bardziej pracochłonna: konektory, uprawnienia Kibany, węzeł ML pod ELSER/E5.
- Jakość mocno zależy od wybranego modelu. Słabsze lokalne modele źle radzą sobie z tool callingiem.

---

## 4. Czy są bezpieczne?

### Grafana Assistant

| Aspekt | Stan |
|---|---|
| **Gdzie idą dane** | Prompty i **kontekst zapytań** (zapytania, fragmenty wyników, metadane dashboardów) trafiają do backendu Grafana Cloud, a stamtąd do dostawcy LLM wybranego przez Grafana Labs. Źródła danych zostają u Ciebie, ale **wyniki zapytań, które agent odczyta, opuszczają środowisko**. |
| **Self-hosted** | UI działa lokalnie, ale backend, limity i billing są w podłączonym stacku Cloud. Self-hosting **nie** oznacza, że nic nie wychodzi na zewnątrz. |
| **Uprawnienia** | Assistant działa w kontekście uprawnień użytkownika w Grafanie (RBAC, uprawnienia do datasource'ów). Konto serwisowe dla automatycznych dochodzeń warto ograniczyć do minimum. |
| **Wybór modelu / regionu** | Brak kontroli nad modelem. Region danych zależy od regionu stacka Cloud (wybierz EU). |
| **Zgodność** | Grafana Cloud ma certyfikaty (SOC 2, ISO 27001) i DPA, ale to i tak wymaga akceptacji działu bezpieczeństwa / DPO. |
| **Admin** | Assistanta można wyłączyć lub ograniczyć na poziomie organizacji/stacka. |

**Ryzyka praktyczne:** PII i sekrety w logach (Loki), które agent odczyta i wyśle jako kontekst. Prompt injection przez treść logów. Kosztowne automatyczne dochodzenia przy „hałaśliwych” alertach.

### Elastic AI

| Aspekt | Stan |
|---|---|
| **Gdzie idą dane** | Do dostawcy LLM z konektora: **Twój wybór** (firmowy tenant Azure OpenAI/Bedrock/Vertex, lokalny model albo Elastic Managed LLM). |
| **Anonimizacja** | Dokumentacja Elastic mówi wprost: dane wysyłane do asystenta **nie są domyślnie anonimizowane** (alerty, logi, zapytania, czat). Jest *anonymization pipeline* (preview, reguły RegExp/NER), ale tylko w AI Assistant. **Agent Builder jej nie obsługuje.** |
| **Uprawnienia** | Wymaga uprawnienia Kibany *Observability AI Assistant: All* (lub odpowiednika dla Agent Buildera). Asystent działa w kontekście uprawnień użytkownika do indeksów. Ogranicz je przez role i *document/field level security*. |
| **Air-gap** | Możliwy z lokalnym LLM. To główna przewaga nad Grafaną. |
| **Audyt** | AI Assistant ma pełny audit log; w Agent Builder jest on na razie ograniczony. |
| **Klucze API** | Przechowywane w konektorach Kibany (zaszyfrowane kluczem `xpack.encryptedSavedObjects`). |

### Wspólna checklista przed wdrożeniem

- [ ] Czy polityka firmy pozwala wysyłać logi, metryki i zapytania do zewnętrznego LLM? Do którego dostawcy i w jakim regionie?
- [ ] Czy w logach są PII lub sekrety? Jeśli tak, maskuj je **przy ingestii**, zanim trafią do Lokiego/Elastica, a nie dopiero przed LLM.
- [ ] Minimalne uprawnienia: kto ma dostęp do AI i do jakich datasource'ów/indeksów?
- [ ] Limity kosztów (tokeny / aktywni użytkownicy / Elastic Managed LLM).
- [ ] Automatyczne dochodzenia tylko dla wybranych, niehałaśliwych alertów.
- [ ] AI tylko czyta i proponuje. Zmiany (dashboardy, reguły, akcje) zatwierdza człowiek.

---

## 5. Licencje i koszty: czy potrzebujesz płatnej wersji?

### Grafana

| Scenariusz | Czy jest AI? | Koszt |
|---|---|---|
| **Grafana Cloud Free** | ✅ Assistant: do **3 aktywnych użytkowników AI / mies.**, 40M tokenów na użytkownika, 25M tokenów na użycie systemowe | **0 zł**, bez karty |
| **Grafana Cloud Pro** | ✅ 3 użytkowników w opłacie platformowej (19 USD/mies.), każdy kolejny **20 USD / aktywny użytkownik AI**, dodatkowe tokeny 2 USD / 1M | wg zużycia |
| **Grafana Cloud Enterprise** | ✅ | umowa roczna (od ok. 25 tys. USD/rok) |
| **Grafana OSS self-hosted + połączenie z Cloud** | ✅ Assistant (UI lokalnie, backend i billing w podłączonym stacku Cloud, więc darmowy stack = limity Free) | 0 zł przy darmowym stacku |
| **Grafana Enterprise self-hosted (13.1+)** | ✅ Assistant preinstalowany, ale nadal wymaga połączenia z kontem Cloud | licencja Enterprise + rozliczenie Assistanta wg stacka Cloud |
| **Grafana OSS bez Cloud** | ❌ Brak Assistanta. Tylko **LLM plugin** (darmowy, Twój klucz API) z drobnymi funkcjami, albo **mcp-grafana** + zewnętrzny asystent (Claude Code, Cursor) | 0 zł + koszt Twojego LLM |

Uwagi:
- **„Aktywny użytkownik AI”** to każdy, kto w danym miesiącu wysłał wiadomość, kliknął akcję Assistanta (np. *Explain in Assistant*), użył go przez Slack, Teams, CLI lub MCP albo uruchomił automatyzację w trybie użytkownika.
- **Assistant Investigations** korzystają z tych samych puli tokenów, a od **1 października 2026** są osobno rozliczane i mierzone. Sprawdź aktualny cennik.
- Watchers są darmowe w okresie preview.


### Elastic

| Scenariusz | Czy jest AI? | Koszt |
|---|---|---|
| **Self-managed Basic (free)** | ❌ | 0 zł |
| **Self-managed Platinum** | ❌ (AI Assistant/Agent tylko w Enterprise) | licencja |
| **Self-managed Enterprise** | ✅ AI Agent / AI Assistant, Attack Discovery | licencja wg węzłów/RAM + **Twój LLM** |
| **Elastic Cloud Hosted Enterprise** | ✅ (+ opcja Elastic Managed LLM, płatny dodatkowo) | wg zasobów + LLM |
| **Elastic Cloud Serverless** | ✅ w odpowiednim *feature tier* projektu (Observability Complete / Security Complete) | wg zużycia |
| **Trial Elastic Cloud** | ✅ wszystkie funkcje, zwykle z preconfigured LLM | **0 zł przez 14 dni** |
| **Trial self-managed** | ✅ wszystkie funkcje | **0 zł przez 30 dni** (`POST _license/start_trial?acknowledge=true`) |

Uwagi:
- Licencja Elastica **nie obejmuje kosztów LLM**. Przy własnym konektorze płacisz dostawcy (OpenAI, Azure, AWS…). Elastic Managed LLM jest płatny osobno, poza trialem.
- Funkcja Knowledge Base wymaga węzła ML (ok. 4 GB RAM) pod ELSER lub E5, co oznacza dodatkowy koszt zasobów w Cloud Hosted.


---

## 6. Instalacja i użycie

### 6.1 Grafana Assistant w Grafana Cloud (najprostsza ścieżka)

1. Załóż konto na https://grafana.com/auth/sign-up (plan Free, bez karty), wybierz region **EU**.
2. Otwórz swój stack (`https://<stack>.grafana.net`).
3. Kliknij ikonę **Assistant** w prawym górnym rogu i zaakceptuj warunki przy pierwszym użyciu (robi to admin organizacji).
4. Podłącz dane. Najszybciej: **Connections → Kubernetes Monitoring** (Alloy przez Helm) albo dane demo.

Przykładowe prompty:

```
Pokaż p95 czasu odpowiedzi HTTP dla serwisu checkout z ostatnich 6 godzin, rozbite na endpointy.

Napisz zapytanie LogQL, które zliczy błędy 5xx w namespace shop na minutę.

Zbuduj dashboard dla mojego klastra K8s: CPU i RAM per namespace, restarty podów, pody w stanie Pending.

Wyjaśnij, co pokazuje ten panel i dlaczego o 14:05 jest skok.

Zbadaj, dlaczego alert HighErrorRate dla serwisu cart odpalił 20 minut temu.
```

### 6.2 Grafana Assistant w Grafanie self-hosted (OSS/Enterprise 13.0+)

Wymagany stack Grafana Cloud (może być Free) i rola admina organizacji w lokalnej Grafanie.

```bash
# Grafana OSS: instalacja aplikacji Assistant
grafana cli plugins install grafana-assistant-app
# (Grafana Enterprise 13.1+: aplikacja jest preinstalowana)
sudo systemctl restart grafana-server
```

Potem w UI: **Administration → Plugins and data → Apps → Grafana Assistant → Connect to Grafana Cloud**, a następnie zaloguj się do konta Cloud i wybierz stack. W Helm chartcie / Dockerze plugin dodasz przez `GF_PLUGINS_PREINSTALL=grafana-assistant-app`.

> Dokładna nazwa pluginu i ekranów może się różnić między wydaniami. Sprawdź stronę „Set up Grafana Assistant in self-managed Grafana”.

### 6.3 Alternatywa bez Cloud: LLM plugin lub mcp-grafana

```bash
# LLM plugin (Twój klucz API: OpenAI, Azure, Anthropic lub OpenAI-compatible, np. Ollama)
grafana cli plugins install grafana-llm-app
# Konfiguracja: Administration → Plugins → LLM → wybór dostawcy, klucz API, model
```

```bash
# mcp-grafana: Grafana jako narzędzie dla Claude Code
# 1. Utwórz Service Account w Grafanie (rola Viewer) i token
# 2. Dodaj serwer MCP
claude mcp add grafana \
  -e GRAFANA_URL=http://localhost:3000 \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN=glsa_xxx \
  -- docker run --rm -i -e GRAFANA_URL -e GRAFANA_SERVICE_ACCOUNT_TOKEN mcp/grafana -t stdio
```

Potem w Claude Code: *„Sprawdź w Grafanie, które pody w namespace shop mają najwięcej restartów i pokaż logi z Lokiego”*.

### 6.4 Elastic: lab self-managed z trialem

```bash
# Najszybciej: oficjalny skrypt start-local (Elasticsearch + Kibana w Dockerze, od razu z trialem)
curl -fsSL https://elastic.co/start-local | sh
# Kibana: http://localhost:5601 (hasło w pliku .env w katalogu elastic-start-local)

# Jeśli klaster już stoi na Basic, włącz 30-dniowy trial:
curl -u elastic:$ELASTIC_PASSWORD -X POST \
  "http://localhost:9200/_license/start_trial?acknowledge=true"
```

**Konfiguracja konektora LLM** (UI: *Stack Management → Connectors → Create connector → OpenAI / Amazon Bedrock / Google Gemini / AI Connector*) albo przez API:

```bash
curl -u elastic:$ELASTIC_PASSWORD -X POST "http://localhost:5601/api/actions/connector" \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' -d '{
  "name": "Azure OpenAI - szkolenie",
  "connector_type_id": ".gen-ai",
  "config": {
    "apiProvider": "Azure OpenAI",
    "apiUrl": "https://<nazwa>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-10-21"
  },
  "secrets": { "apiKey": "<KLUCZ>" }
}'
```

Lokalny model (np. Ollama lub LM Studio) podłączysz przez konektor OpenAI z `apiProvider: "Other"` i adresem `http://<host>:11434/v1/chat/completions`. Kibana w Dockerze musi widzieć ten host.

**Uprawnienia:** utwórz rolę z dostępem do potrzebnych indeksów (`logs-*`, `metrics-*`, `traces-*`) i uprawnieniem Kibany *Observability AI Assistant: All* / *Agent Builder*, a potem przypisz ją użytkownikom.

**Opcjonalnie: Knowledge Base** (tylko w klasycznym AI Assistant): *AI Assistant → Settings → Knowledge Base → Install* (ELSER dla angielskiego, E5 dla wielu języków, w tym polskiego). Potem dodaj runbooki ręcznie, importem NDJSON albo konektorem (GitHub, Confluence).

**Wybór czatu (9.4+):** globalne wyszukiwanie → *GenAI Settings* → *Chat Experience* → **AI Agent** (domyślny) albo **AI Assistant** (z KB i anonimizacją).

Przykładowe prompty (Observability):

```
Jakie usługi miały najwięcej błędów w ostatniej godzinie? Pokaż zapytanie ES|QL.

Pokaż logi z namespace shop zawierające "OOMKilled" z ostatnich 24h i pogrupuj po podach.

Wyjaśnij ten alert i zaproponuj możliwe przyczyny.

Czy w metrykach CPU usługi cart widać change point w ciągu ostatnich 6 godzin?
```

Przykładowe ES|QL, które asystent powinien wygenerować (wzorzec do porównania z tym, co wygeneruje asystent):

```esql
FROM logs-*
| WHERE @timestamp > NOW() - 1 hour AND log.level == "error"
| STATS errors = COUNT(*) BY service.name
| SORT errors DESC
| LIMIT 10
```

### 6.5 Elastic Cloud (trial 14 dni)

1. Zarejestruj się na https://cloud.elastic.co/registration, wybierz **Observability (Serverless)** albo Hosted, region w EU.
2. Dane: *Add data → Kubernetes* (Elastic Agent / OpenTelemetry przez Helm) albo dane przykładowe.
3. Kliknij **AI Agent** w prawym górnym rogu. Preconfigured LLM działa od razu, bez własnego klucza.

---

## Źródła

- Grafana Assistant: https://grafana.com/docs/grafana-cloud/machine-learning/assistant/
- Cennik Assistanta: https://grafana.com/docs/grafana-cloud/platform/pricing-and-usage/assistant/ · https://grafana.com/pricing/
- Assistant w self-managed Grafanie: https://grafana.com/docs/grafana-cloud/platform/grafana-assistant/get-started/self-managed/
- Assistant on-prem (04.2026): https://grafana.com/whats-new/2026-04-21-grafana-assistant-becomes-available-on-prem/
- Assistant preinstalowany w Grafana Enterprise (06.2026): https://grafana.com/whats-new/2026-06-23-grafana-assistant-is-now-pre-installed-in-grafana-enterprise/
- Grafana LLM plugin: https://grafana.com/grafana/plugins/grafana-llm-app/ · https://github.com/grafana/grafana-llm-app
- mcp-grafana: https://github.com/grafana/mcp-grafana
- Elastic AI Assistant for Observability: https://www.elastic.co/docs/solutions/observability/ai/observability-ai-assistant
- Agent Builder vs AI Assistant: https://www.elastic.co/docs/explore-analyze/ai-features/ai-chat-experiences/ai-agent-or-ai-assistant
- Agent Builder — start: https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/get-started
- Subskrypcje Elastic: https://www.elastic.co/subscriptions
