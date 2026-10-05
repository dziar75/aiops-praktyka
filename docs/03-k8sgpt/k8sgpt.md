# k8sgpt — skaner klastra Kubernetes z wyjaśnieniami AI

Materiał pomocniczy do Dnia 1, temat 1.4.3. Diagram architektury: [`architektura.html`](architektura.html). Drugie narzędzie z tego tematu: [`../04-robusta/robusta.md`](../04-robusta/robusta.md).

> Stan na październik 2026 (k8sgpt 0.4.39). Wersje i funkcje zmieniają się szybko, więc przed szkoleniem sprawdź README projektu.

---

## TL;DR

| | |
|---|---|
| **Jednym zdaniem** | Skaner klastra, który znajduje problemy regułami i opcjonalnie tłumaczy je po ludzku przez LLM |
| **Wyzwalacz** | Ty uruchamiasz `k8sgpt analyze` (albo cyklicznie operator w klastrze) |
| **Gdzie działa** | CLI na laptopie, operator w klastrze albo serwer MCP dla asystenta |
| **Wynik** | Lista problemów (+ wyjaśnienie i sugerowana poprawka z `--explain`) |
| **AI** | Opcjonalne; bez niego działa jak deterministyczny linter stanu klastra |
| **Licencja** | Apache 2.0, projekt CNCF Sandbox |
| **Popularność (GitHub)** | ~8,2k ★ |

**Najkrócej:** k8sgpt odpowiada na pytanie *„co jest teraz zepsute w klastrze?”*.

---

## 1. Jak działa

### Krok 1: wykrywanie (zawsze bez AI)

`k8sgpt analyze` czyta zasoby przez API serwera, tak jak `kubectl get`, i przepuszcza je przez zestaw **analyzerów**: Pod, Deployment, ReplicaSet, StatefulSet, Service, Ingress, PVC, Node, HPA, PDB, NetworkPolicy, CronJob, Job, ConfigMap, Gateway API i inne. Każdy analyzer to **deterministyczna reguła w Go**, np.:

- Pod w `CrashLoopBackOff` albo `ImagePullBackOff` → błąd,
- Service ma selektor, ale zero endpointów → błąd,
- PVC w `Pending`, bo StorageClass nie istnieje → błąd,
- ConfigMap nieużywana przez żaden pod → błąd (stąd szum, patrz sekcja 7).

Wynik to lista: zasób + surowy tekst błędu. Wszystko dzieje się lokalnie, nic nie wychodzi na zewnątrz.

### Krok 2: wyjaśnianie (AI, tylko z `--explain`)

Dla **każdego** znalezionego błędu k8sgpt wysyła do LLM-a jedno zapytanie zbudowane z szablonu promptu. Domyślny szablon (z pamięci, do sprawdzenia w źródłach) brzmi mniej więcej tak: *„Simplify the following Kubernetes error message… Provide the most possible solution in a step by step style in no more than 280 characters. Format: Error: … Solution: …”*.

Co z tego wynika:
- **Model nie wybiera, co sprawdzić.** Dostaje gotowy tekst błędu. Nie czyta logów, nie robi `describe`, niczego nie dopytuje.
- **AI nie wykrywa problemów.** Jeśli żadna reguła nie złapała błędu, LLM w ogóle o nim nie usłyszy.
- **Limit ~280 znaków** tłumaczy, dlaczego odpowiedzi bywają banalne („sprawdź logi”).
- **Cache:** odpowiedzi są zapisywane lokalnie. Ten sam błąd przy kolejnym uruchomieniu nie idzie ponownie do modelu (`--no-cache` to wyłącza). Przyda się, gdy na demie wynik „nie chce się zmienić”.

Najkrócej: **k8sgpt = reguły wykrywają, LLM tłumaczy.** W HolmesGPT jest odwrotnie: LLM sam decyduje, jakie komendy uruchomić, i robi to w pętli.

### Skąd model?

k8sgpt **nie ma wbudowanego modelu**. `--explain` korzysta z backendu skonfigurowanego przez `k8sgpt auth add`: OpenAI, Anthropic, Azure OpenAI, Bedrock, Vertex, Ollama, LocalAI i inne, a od 0.4.39 także `litellm`. Subskrypcja Claude czy ChatGPT nie wystarczy: k8sgpt potrzebuje API (klucz + endpoint). Kilka backendów może współistnieć; `k8sgpt auth default` wybiera domyślny, a `--backend` nadpisuje go przy jednym uruchomieniu.

**U nas:** backend `litellm` → `https://llm.aiops.marniok.dev/v1` → Claude Haiku 4.5. Klucz w configu k8sgpt to klucz wirtualny LiteLLM (budżet per osoba), nie klucz Anthropic. Szczegóły bramy: [`../02-litellm/litellm.md`](../02-litellm/litellm.md).

---

## 2. Co widzi, a czego nie

k8sgpt sprawdza **migawkę stanu obiektów**: wszystko, co jest zapisane w obiektach Kubernetesa w chwili uruchomienia.

| Widzi | Nie widzi |
|---|---|
| **Błędną konfigurację:** Service z selektorem bez podów, Ingress do nieistniejącego Service, PVC z nieistniejącą StorageClass | **Metryk:** CPU 95%, pamięć tuż pod limitem |
| **Stan obiektów (`status`):** CrashLoopBackOff, ImagePullBackOff, Pending, node `NotReady`, Deployment z niedostępnymi replikami, nieudany Job | **Latencji i błędów 5xx** przy zielonych podach |
| Pod, który po kolejnych OOMKill wpadł w CrashLoopBackOff | **Pojedynczego OOMKill**, po którym pod jest znów `Running` |
| | **Treści logów aplikacji** i historii („co noc o 2:00”) |
| | NetworkPolicy, która blokuje ruch, ale jest poprawna składniowo |

Pod może być `Running` i formalnie zdrowy, a aplikacja odpowiada po 10 sekundach. Dla k8sgpt wszystko jest wtedy w porządku. **Zielony wynik k8sgpt nie znaczy, że aplikacja działa.** To triage, nie monitoring.

---

## 3. Trzy tryby pracy

### CLI na laptopie (to używamy na szkoleniu)

Uruchamiasz na żądanie, z uprawnieniami swojego kubeconfigu. Operator w klastrze nie jest potrzebny. Do diagnozy ad hoc, do CI (`--output json`), na klastrze, na którym nie wolno nic instalować.

### Operator w klastrze

`k8sgpt-operator` (Helm) dodaje dwa CRD:
- **`K8sGPT`**: konfiguracja (backend, model, Secret z kluczem, `anonymized`, filtry, opcjonalnie sink do Slacka),
- **`Result`**: jeden obiekt na każde znalezisko. Gdy problem zniknie, obiekt też znika.

Operator stawia w klastrze k8sgpt jako serwer i **cyklicznie** uruchamia analizę (interwał: sprawdź w README operatora). Wyniki:

```bash
kubectl get results -A
kubectl get result <nazwa> -n k8sgpt-operator-system -o yaml   # błąd + wyjaśnienie AI
```

| | CLI | Operator |
|---|---|---|
| Kiedy działa | gdy Ty uruchomisz | cały czas, cyklicznie |
| Wynik | tekst na ekranie | obiekty `Result`, widoczne dla każdego z `kubectl` |
| Integracje | stdout / JSON | **metryki dla Prometheusa** (alert, dashboard w Grafanie), **powiadomienia** do Slacka / webhooka |
| Uprawnienia | Twój kubeconfig | własny ServiceAccount z RBAC z Helm chartu |
| Klucz do LLM | plik na laptopie, jawnym tekstem | Secret w klastrze |
| Koszt AI | tylko gdy uruchomisz | każde **nowe** znalezisko to wywołanie LLM; cache ogranicza powtórki |
| Naprawa | brak | eksperymentalna auto-remediacja (sprawdź aktualny stan) |

Na co uważać przy operatorze:
- **Szum zamienia się w koszty i powiadomienia.** Na naszym EKS bez filtrów od razu ok. 22 `Result`, z czego 21 to szum; z AI to 22 płatne wywołania, z sinkiem 22 wiadomości.
- **Nadal widzi tylko stan obiektów** i **nadal to pull**: sam sprawdza w kółko, ale nie reaguje na alerty z Prometheusa. To inna rola niż Robusta.
- **RBAC:** przejrzyj ClusterRole z Helm chartu, bo operator czyta zasoby w całym klastrze.

### Serwer MCP

`k8sgpt serve --mcp` wystawia analizę jako narzędzie dla asystenta (Claude Code, Claude Desktop, Cursor). Wtedy role się odwracają: **asystent jest agentem**, a k8sgpt dostarcza mu deterministyczne reguły. Pilnuj, czy serwer MCP nie wystawia też operacji modyfikujących.

---

## 4. Jaką ma opinię?

**Plusy:**
- Najszybsze „wow” w AIOps dla Kubernetesa: jedna komenda i od razu widać wynik. Dlatego chętnie pokazuje się go na szkoleniach i konferencjach.
- Analyzery działają też **bez AI**, co wiele osób uważa za największą wartość tego narzędzia.
- Obsługuje **lokalne modele** (Ollama, LocalAI), więc da się go używać w środowiskach odciętych od sieci.
- Projekt CNCF, licencja Apache 2.0, aktywna społeczność, odznaka OpenSSF Best Practices.

**Minusy (często podnoszone na Reddicie i HN):**
- Wyjaśnienia AI bywają **banalne**: „Pod jest w CrashLoopBackOff, sprawdź logi”. Doświadczony admin wie to bez LLM-a.
- Widzi tylko to, co wynika ze statusu obiektów. Przy trudnych problemach (wydajność, sieć między usługami, błędy aplikacji) niewiele pomaga.
- Halucynacje w sugerowanych poprawkach, np. nieistniejące pola YAML albo złe nazwy flag. **Każdą sugestię trzeba zweryfikować.**
- W porównaniu z agentami (HolmesGPT, Claude Code + kubectl, kubectl-ai) to bardziej „statyczne” podejście.

**Ogólny werdykt:** świetne narzędzie edukacyjne i do szybkiego triage'u, ale nie zastąpi doświadczonego SRE ani pełnego stacku observability.

---

## 5. Czy jest bezpieczny?

Krótka odpowiedź: **samo narzędzie jest w porządku, ale ryzyko leży w tym, jakie dane trafiają do LLM i jakie uprawnienia ma narzędzie w klastrze.** Te same ryzyka dotyczą Robusty i HolmesGPT.

### Ryzyka wspólne dla narzędzi AI w diagnostyce Kubernetesa

| Ryzyko | Opis | Mitygacja |
|---|---|---|
| **Wyciek danych do dostawcy LLM** | Nazwy zasobów, namespace'ów, obrazów, fragmenty logów i eventów trafiają do OpenAI/Anthropic/Azure itd. W logach bywają tokeny, e-maile, PII. | Lokalny model (Ollama) albo firmowy endpoint (Azure OpenAI, Bedrock w Twoim tenancie, firmowa brama), anonimizacja, filtrowanie, zgoda działu bezpieczeństwa |
| **Uprawnienia w klastrze** | Narzędzie potrzebuje szerokiego `get/list/watch`, często cluster-wide. Odczyt `Secrets` jest szczególnie wrażliwy. | Dedykowany ServiceAccount, RBAC read-only, wykluczenie `secrets`, ograniczenie do namespace'ów |
| **Prompt injection** | Złośliwa treść w logach, adnotacjach lub nazwach zasobów może sterować modelem, zwłaszcza agentem. | Tryb read-only, brak akcji zapisujących bez akceptacji człowieka |
| **Halucynacje → zła naprawa** | Model proponuje błędną komendę, a ktoś ją wykonuje na produkcji. | Zasada „AI jako junior do weryfikacji”, review każdej sugestii |
| **Klucze API** | Klucz do LLM leży w configu lub Secrecie. | Secret manager, rotacja, limity kosztów (u nas: budżety w LiteLLM) |

### Specyfika k8sgpt

- `--anonymize` maskuje nazwy obiektów (Pod, Deployment, Namespace) przed wysłaniem i odmaskowuje je w odpowiedzi. **Nie obejmuje** wszystkich analyzerów ani treści eventów i logów. Nie traktuj jej jako gwarancji.
- Bez `--explain` **nic nie wychodzi poza klaster i laptop**.
- CLI korzysta z Twojego `kubeconfig`: jeśli jesteś cluster-adminem, k8sgpt też nim jest.
- Konfiguracja z kluczem leży **jawnym tekstem** w `~/.config/k8sgpt/k8sgpt.yaml` (macOS: `~/Library/Application Support/k8sgpt/k8sgpt.yaml`).
- Tryb MCP: pilnuj, czy serwer nie wystawia operacji modyfikujących.

### Checklista przed wdrożeniem w firmie

- [ ] Czy polityka firmy pozwala wysyłać metadane i logi klastra do zewnętrznego LLM?
- [ ] Który endpoint LLM (publiczny / firmowy tenant / brama / lokalny)?
- [ ] Dedykowany ServiceAccount z minimalnym RBAC, bez dostępu do `secrets`?
- [ ] Anonimizacja włączona, filtry analyzerów i namespace'ów ustawione?
- [ ] Brak automatycznych akcji zapisujących bez akceptacji człowieka?
- [ ] Limity kosztów po stronie dostawcy LLM albo bramy?

---

## 6. Instalacja i użycie

### 6.1 CLI

```bash
# macOS / Linux (Homebrew)
brew install k8sgpt

# Debian/Ubuntu: .deb z GitHub Releases
curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/latest/download/k8sgpt_amd64.deb
sudo dpkg -i k8sgpt_amd64.deb

k8sgpt version
```

**Backend AI na szkoleniu (LiteLLM)** — klucz z karty dostępowej:


```bash
k8sgpt auth add --backend litellm --baseurl https://llm.aiops.marniok.dev/v1 \
  --model claude-haiku-4-5 --password <klucz-LiteLLM>
k8sgpt auth default --provider litellm
k8sgpt auth list
```

**Inne backendy (do pokazania, że to tylko konfiguracja):**

```bash
k8sgpt auth add --backend anthropic --model claude-haiku-4-5          # Anthropic wprost
k8sgpt auth add --backend azureopenai --baseurl https://<nazwa>.openai.azure.com/ \
  --engine <deployment-name> --model gpt-4o                           # firmowy tenant
ollama pull llama3.1
k8sgpt auth add --backend ollama --model llama3.1 --baseurl http://localhost:11434   # lokalnie
```

**Użycie:**

```bash
k8sgpt analyze --namespace <ns>                                # same reguły, nic nie wychodzi
k8sgpt analyze --namespace <ns> --explain                      # + wyjaśnienie z LLM
k8sgpt analyze --namespace <ns> --explain --anonymize          # nazwy zamaskowane
k8sgpt analyze --namespace <ns> --explain --language polish    # odpowiedź po polsku
k8sgpt analyze --explain --filter Pod,Service --output json    # do CI / jq
k8sgpt analyze --explain --no-cache                            # wymuś nowe wywołanie modelu

k8sgpt filters list                                            # analyzery
k8sgpt integration activate trivy                              # integracja z Trivy
k8sgpt serve --mcp                                             # serwer MCP dla asystenta
```

**Przykładowy wynik:**

```
0: Pod shop/cart-7d9f8b6c5-x2k4p(Deployment/cart)
- Error: back-off 5m0s restarting failed container=cart pod=cart-7d9f8b6c5-x2k4p
Error: The container is repeatedly crashing on startup.
Solution:
1. Check logs: kubectl logs cart-7d9f8b6c5-x2k4p -n shop --previous
2. Verify required env variables / ConfigMap references exist.
3. Check resource limits — the container may be OOMKilled.
```

### 6.2 Operator w klastrze

```bash
helm repo add k8sgpt https://charts.k8sgpt.ai/
helm repo update
helm install k8sgpt-operator k8sgpt/k8sgpt-operator \
  -n k8sgpt-operator-system --create-namespace

kubectl create secret generic k8sgpt-llm \
  --from-literal=api-key=<klucz> -n k8sgpt-operator-system
```

```yaml
# k8sgpt.yaml
apiVersion: core.k8sgpt.ai/v1alpha1
kind: K8sGPT
metadata:
  name: k8sgpt
  namespace: k8sgpt-operator-system
spec:
  ai:
    enabled: true
    backend: openai          # przy bramie zgodnej z OpenAI dodaj baseUrl (sprawdź pole w CRD)
    model: gpt-4o-mini
    anonymized: true
    secret:
      name: k8sgpt-llm
      key: api-key
  noCache: false
  repository: ghcr.io/k8sgpt-ai/k8sgpt
  # version: v0.4.x   # przypnij wersję
  # sink:
  #   type: slack
  #   webhook: <url>
```

```bash
kubectl apply -f k8sgpt.yaml
kubectl get results -A
```

---

## k8sgpt a Robusta

Pełne porównanie: [`../04-robusta/robusta.md`](../04-robusta/robusta.md), sekcja „Robusta a k8sgpt”. W skrócie: k8sgpt to **pull** („sprawdzam, co jest zepsute”), Robusta to **push** („dostałem alert, dlaczego?”). Narzędzia się uzupełniają: k8sgpt na triage, Robusta na on-call.

---

## Źródła

- k8sgpt: https://github.com/k8sgpt-ai/k8sgpt · https://docs.k8sgpt.ai
- k8sgpt-operator: https://github.com/k8sgpt-ai/k8sgpt-operator
