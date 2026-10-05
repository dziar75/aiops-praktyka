# LiteLLM — brama do modeli AI (AI gateway)

Diagram architektury: [`architektura.html`](architektura.html). LiteLLM pojawia się w kilku miejscach szkolenia:
- **Dzień 1, temat 1:** modele chmurowe a polityki firmowe; brama jako punkt kontroli.
- **Dzień 1, temat 2:** jak asystent łączy się z modelem; Claude Code przez bramę.
- **Dzień 1, temat 4:** backend k8sgpt.
- **Dzień 3:** HolmesGPT, agent z labu i atak na łańcuch dostaw w temacie Trivy.

> Stan na 3.10.2026, LiteLLM v1.103.2. Fragmenty oznaczone „sprawdzone 3.10” przetestowaliśmy na naszym
> środowisku. Resztę opisuje dokumentacja projektu:
> [docs.litellm.ai](https://docs.litellm.ai).

---

## TL;DR

| | |
|---|---|
| **Co to jest** | Open-source'owa brama (proxy) do ponad 100 dostawców modeli. Wystawia jedno API (format OpenAI, a także Anthropic `/v1/messages`) i tłumaczy je na API dostawcy. |
| **Dwie formy** | **Biblioteka Pythona** (`import litellm`) i **serwer proxy** (AI gateway), czyli to, czego używamy na szkoleniu. |
| **Po co** | Klucz dostawcy zostaje w jednym miejscu. Do tego klucze wirtualne per osoba, budżety, limity, rozliczanie kosztów, logi zapytań, guardrails i zmiana dostawcy bez ruszania narzędzi. |
| **Czym NIE jest** | Nie jest modelem ani agentem i niczego nie „rozumie”. To infrastruktura między narzędziem a modelem. |
| **Licencja** | MIT. Wyjątek: katalog `enterprise/` ma osobną licencję komercyjną (m.in. SSO, audyt). |
| **Popularność** | Ok. 60 tys. gwiazdek na GitHubie (10.2026). Biblioteka jest używana wewnątrz innych narzędzi, np. HolmesGPT i agentów. |
| **Ryzyko do zapamiętania** | W marcu 2026 złośliwe wersje 1.82.7 i 1.82.8 trafiły na PyPI przez przejęty pipeline CI (punkt 6). |

---

## 1. Do czego służy

Bez bramy każde narzędzie ma własny klucz do dostawcy, własny format API i własne, niewidoczne koszty:

```
k8sgpt ──(klucz A)──▶ OpenAI
agent  ──(klucz B)──▶ Anthropic          ← kto ile wydał? kto ma który klucz? jak zablokować jedną osobę?
Holmes ──(klucz C)──▶ Bedrock
```

Z bramą wszystko idzie przez jedno miejsce:

```
k8sgpt / kubectl-ai / HolmesGPT / agent / Claude Code
        │  jeden adres + klucz wirtualny osoby (sk-…)
        ▼
   LiteLLM proxy ── klucze dostawców (tylko tutaj), budżety, limity, logi, guardrails
        │
        ▼
   Anthropic API / Bedrock / Azure OpenAI / Vertex / Ollama / …
```

Co daje brama, punkt po punkcie:
1. **Jedno API.** Narzędzie zna tylko format OpenAI, a z tyłu jest Claude. Działa też odwrotnie: Claude Code
   mówi formatem Anthropic, a LiteLLM może z tyłu skierować go np. do Bedrocka.
2. **Klucze wirtualne.** Każda osoba lub zespół ma własny klucz z budżetem, listą modeli, limitem zapytań na minutę
   (RPM) i tokenów na minutę (TPM) oraz datą ważności. Klucz można zablokować bez ruszania pozostałych.
3. **Koszty.** Zapis każdego zapytania: kto, jaki model, ile tokenów, ile dolarów. Raporty per klucz, zespół i tag.
4. **Niezawodność.** Fallbacki (gdy model A zwraca błąd albo limit, użyj B), load balancing między wdrożeniami,
   ponawianie zapytań, cache odpowiedzi (np. Redis).
5. **Guardrails.** Filtry przed i po wywołaniu modelu, np. maskowanie danych osobowych (Presidio), blokowane słowa,
   wykrywanie prompt injection, zewnętrzne usługi moderacji.
6. **Obserwowalność.** Logi do Langfuse, OpenTelemetry, Datadog, S3 i innych. Metryki Prometheusa
   (w nowszych wersjach część jest płatna, sprawdź przed użyciem).
7. **Zmiana dostawcy w jednym miejscu.** Jeśli Bedrock na naszym koncie kiedyś dostanie normalne limity,
   zmieniamy jedną linię w konfiguracji, a uczestnicy i narzędzia niczego nie zauważą.

---

## 2. Trzy „twarze” LiteLLM: Swagger, panel admina i API

### Swagger: `https://llm.aiops.marniok.dev/`
Strona startowa proxy to **dokumentacja API (Swagger UI)**: ponad 600 endpointów w grupach. Przydatne, gdy chcesz
zobaczyć, co da się zrobić z API. Do codziennej pracy jest panel admina. Najważniejsze grupy:

| Grupa w Swaggerze | Co tam jest |
|---|---|
| `chat/completions`, `/v1/messages`, `embeddings`, `responses` | Wywołania modeli: format OpenAI i format Anthropic |
| `key management` | `/key/generate`, `/key/info`, `/key/block`, `/key/delete` |
| `Budget & Spend Tracking` | `/spend/logs`, raporty wydatków |
| `model management` | Dodawanie i edycja modeli w locie (u nas modele są w ConfigMapie) |
| `team management`, `Internal User management` | Zespoły, użytkownicy, ich budżety |
| `guardrails` | Rejestracja i test filtrów |
| `llm_passthrough` | Przekazanie zapytania 1:1 do natywnego API dostawcy (np. Bedrock, Vertex) |
| `health` | `/health/liveliness`, `/health/readiness` (używane przez Kubernetes) |

### Panel admina: `https://llm.aiops.marniok.dev/ui`
- **Virtual Keys:** lista kluczy, budżety, wydatki, blokowanie, tworzenie nowych.
- **Usage:** wydatki w czasie, per klucz, model i zespół. Gotowe do rozliczenia z Sages.
- **Logs:** każde zapytanie: model, tokeny, koszt, czas, status. Treść promptu i odpowiedzi też, bo mamy włączone
  `store_prompts_in_spend_logs: true` (od 4.10; starsze zapytania nie mają treści). W API treść promptu jest w polu
  `proxy_server_request`, pole `messages` zostaje puste. Sprawdzone 4.10.
- **Models:** modele i ich ceny.
- **Teams / Internal Users:** u nas nieużywane, wystarczają klucze per osoba.
- **Playground (Test Key):** czat z modelem wybranym kluczem, wygodny do szybkiego pokazu.

> Dokumentacja LiteLLM zaleca, żeby po pierwszym logowaniu utworzyć własnego użytkownika `proxy_admin`
> i wyłączyć logowanie kluczem głównym (`disable_env_credential_login: true`). Na 3-dniowym szkoleniu z dostępem
> tylko z listy IP to przesada, ale w firmie jest to obowiązkowe.

### API (to, czego używają narzędzia)
```bash
# Format OpenAI: k8sgpt, kubectl-ai, większość SDK i frameworków
curl https://llm.aiops.marniok.dev/v1/chat/completions \
  -H "Authorization: Bearer $KLUCZ" -H 'Content-Type: application/json' \
  -d '{"model":"claude-haiku-4-5","messages":[{"role":"user","content":"Wyjaśnij CrashLoopBackOff jednym zdaniem"}]}'

# Format Anthropic: Claude Code, Anthropic SDK (sprawdzone 3.10)
curl https://llm.aiops.marniok.dev/v1/messages \
  -H "x-api-key: $KLUCZ" -H 'anthropic-version: 2023-06-01' -H 'content-type: application/json' \
  -d '{"model":"claude-haiku-4-5","max_tokens":200,"messages":[{"role":"user","content":"…"}]}'
```

---

## 3. Jak jest u nas (szkolenie)

| Element | Wartość |
|---|---|
| Adres | `https://llm.aiops.marniok.dev` (z zewnątrz, tylko z listy IP), `http://litellm.ai:4000` (w klastrze) |
| Modele | `claude-haiku-4-5` (domyślny: k8sgpt, kubectl-ai), `claude-sonnet-5-5` (agent, HolmesGPT) |
| Ceny | Wpisane ręcznie w ConfigMapie (USD za token), więc budżety działają, nawet gdy LiteLLM nie zna modelu |
| Klucze | każdy uczestnik 5 USD, ważne 7 dni, 30 zapytań/min |


### Dwie pułapki, które wyszły w testach (sprawdzone 3.10)
1. **Parametry próbkowania.** k8sgpt wysyła `temperature` i `top_p`. Haiku 4.5 nie przyjmuje ich razem,
   a Sonnet 5.5 odrzuca każde niestandardowe. Rozwiązanie: `additional_drop_params` w konfiguracji modelu.
   LiteLLM wycina te parametry, zanim zapytanie trafi do Anthropic. To dobry przykład, po co jest warstwa
   pośrednia: **narzędzie się nie zmienia, zmienia się konfiguracja bramy.**
2. **Sonnet 5.5 i `max_tokens`.** Model domyślnie myśli, a myślenie liczy się do limitu. Przy `max_tokens: 50`
   cała odpowiedź poszła na myślenie: `content: null`, `finish_reason: length`, `reasoning_tokens: 50`.
   Przy 1000 działa. Przy okazji to dobry slajd do tematu 1.1 (tokeny).

---

## 4. Narzędzia na szkoleniu i LiteLLM

| Narzędzie | Jak łączy się z LiteLLM | Gdzie na szkoleniu |
|---|---|---|
| **k8sgpt** | Wbudowany backend `litellm` (od 0.4.39): `k8sgpt auth add --backend litellm --baseurl https://llm.aiops.marniok.dev/v1 --model claude-haiku-4-5 --password <klucz>` (sprawdzone 3.10) | demo k8sgpt, lab02 |
| **kubectl-ai** | Format OpenAI z własnym adresem: `--llm-provider=openai`, `OPENAI_ENDPOINT=https://llm.aiops.marniok.dev/v1`, `OPENAI_API_KEY=<klucz>` (wg README kubectl-ai) | dzień 2, lab04 |
| **HolmesGPT** | Używa **biblioteki** LiteLLM wewnętrznie. Model `openai/claude-sonnet-5-5` i `api_base` naszego proxy albo bezpośrednio `anthropic/…` | demo Robusta + Holmes |
| **Agent z dnia 3** | Anthropic SDK albo OpenAI SDK z `base_url` proxy i kluczem uczestnika | Lab dnia 3 |

## 6. Bezpieczeństwo

### Incydent z marca 2026: przejęte wydania na PyPI
- **24.03.2026** na PyPI pojawiły się złośliwe wersje **1.82.7 i 1.82.8**. Według LiteLLM były dostępne ok. 40 minut,
  zanim PyPI je zablokowało. Niektóre firmy bezpieczeństwa podają dłuższe okno.
- **Wektor ataku:** grupa TeamPCP przejęła poświadczenia maintainera do PyPI **przez skompromitowanego Trivy
  używanego w pipeline CI/CD LiteLLM**. Skaner bezpieczeństwa stał się drogą ataku.
- **Ładunek:** kradzież kluczy SSH, poświadczeń chmurowych, **sekretów Kubernetesa** i plików `.env`, narzędzia
  do ruchu bocznego (lateral movement) w Kubernetesie i trwała furtka (backdoor). Wersja 1.82.8 używała pliku
  `.pth`, który uruchamia się przy każdym starcie interpretera Pythona, nawet bez `import litellm`.
- **Oficjalny obraz Docker nie był zagrożony** (zależności przypięte w `requirements.txt`). Wersje ≥ 1.83.0 wychodzą
  z przebudowanego pipeline'u. Nasz obraz v1.103.2 jest z oficjalnego rejestru `ghcr.io/berriai`.
- **Wnioski na szkolenie:**
  - brama AI to **sejf z kluczami do wszystkich modeli**, więc jest atrakcyjnym celem;
  - przypinaj wersje, weryfikuj podpisy obrazów (LiteLLM zaleca `cosign`), izoluj sekrety CI;
  - narzędzia bezpieczeństwa w pipeline też są zależnościami, które trzeba pilnować.

Źródła: [komunikat LiteLLM](https://docs.litellm.ai/blog/security-update-march-2026),
[Datadog Security Labs](https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/),
[Trend Micro](https://www.trendmicro.com/en_us/research/26/c/inside-litellm-supply-chain-compromise.html).

### Checklista bramy AI w firmie
- [ ] Klucz główny i klucze dostawców tylko w menedżerze sekretów; logowanie kluczem głównym do panelu wyłączone (SSO lub własni admini).
- [ ] Klucz wirtualny per osoba lub usługa, z budżetem, RPM i datą ważności. Żadnych współdzielonych kluczy.
- [ ] Endpoint niedostępny publicznie (sieć wewnętrzna, VPN, lista IP).
- [ ] Zapis treści promptów świadomie włączony albo wyłączony (dane osobowe!), retencja logów.
- [ ] Guardrails na dane wrażliwe (maskowanie PII) przed wysłaniem do dostawcy.
- [ ] Przypięta wersja obrazu i proces aktualizacji. Brama musi nadążać za nowymi funkcjami modeli i narzędzi
      (np. Claude Code: [wymagania wobec bramy](https://code.claude.com/docs/en/llm-gateway-protocol)).

---

## 7. Alternatywy (do pytania „a czy jest coś innego?”)

Kategoria nazywa się **AI gateway / LLM gateway**. Rozwiązania tego typu mają m.in. Portkey, Kong (AI Gateway),
Cloudflare (AI Gateway), Envoy (AI Gateway), a od strony chmur Azure API Management (z politykami dla AI).
Anthropic ma Claude apps gateway dla własnych aplikacji. LiteLLM wyróżnia się tym, że jest open source, łatwo go
postawić samodzielnie (self-hosted) i obsługuje najwięcej dostawców. Minus: dużo funkcji i częste wydania, więc
łatwo o regresje (por. pułapki z punktu 3).

---

## 8. Linki

- Dokumentacja: https://docs.litellm.ai (proxy: https://docs.litellm.ai/docs/simple_proxy)
- Panel admina: https://docs.litellm.ai/docs/proxy/ui
- Klucze wirtualne i budżety: https://docs.litellm.ai/docs/proxy/virtual_keys
- Repozytorium: https://github.com/BerriAI/litellm
- Claude Code i bramy: https://code.claude.com/docs/en/llm-gateway
