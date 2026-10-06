# Generowanie konfiguracji — kubectl-ai i AI dla Terraform („Terraform Copilot”)

Materiał pomocniczy do szkolenia „AIOps w praktyce” (mapa narzędzi: *Generowanie konfiguracji*). Diagram architektury: [`architektura.html`](architektura.html).

> Stan na 1 października 2026. Przykłady przygotowane pod **środowisko AWS** (EKS, provider `aws`). Przed szkoleniem sprawdź linki w sekcji Źródła.
>
> 💡 **Uwaga o nazwie:** produkt o nazwie dokładnie „Terraform Copilot” **nie istnieje**. W praktyce to hasło oznacza **AI do pisania Terraform**, czyli zestaw:
> - **GitHub Copilot** (lub Claude Code / Cursor) w edytorze,
> - **Terraform MCP Server** od HashiCorp, który daje AI aktualną wiedzę o providerach i modułach,
> - opcjonalnie funkcje AI w **HCP Terraform** (Infragraph, `tfctl`).
>
> Ten materiał opisuje cały zestaw.

---

## TL;DR

| | **kubectl-ai** | **AI dla Terraform** (Copilot + Terraform MCP) |
|---|---|---|
| **Jednym zdaniem** | Agent w terminalu, który zamienia polecenia w języku naturalnym na operacje `kubectl` i manifesty YAML | Asystent AI w edytorze, który pisze i refaktoryzuje kod Terraform, a dzięki MCP korzysta z aktualnej dokumentacji providerów |
| **Autor** | Google Cloud Platform (projekt społecznościowy, nieoficjalnie wspierany) | GitHub (Copilot), HashiCorp/IBM (Terraform MCP Server, HCP Terraform) |
| **Działa na** | Żywym klastrze (czyta stan, może wykonywać zmiany po akceptacji) | Plikach `.tf` w repozytorium (zmiany w infrastrukturze dopiero przez `plan`/`apply`) |
| **Modele** | Gemini (domyślnie), OpenAI, Azure OpenAI, **AWS Bedrock**, Grok, Ollama, llama.cpp | Copilot: modele OpenAI, Anthropic, Google do wyboru; MCP działa z dowolnym asystentem |
| **Licencja / koszt** | Apache 2.0, darmowy; płacisz za tokeny LLM | Copilot: Free / Pro 10 USD / Business 19 USD / Enterprise 39 USD; Terraform MCP Server: MPL-2.0, darmowy |
| **Największe ryzyko** | Wykonanie złej komendy na żywym klastrze | Wygenerowanie niebezpiecznej lub przestarzałej konfiguracji, która przejdzie review |

**Najkrócej:** kubectl-ai to **„AI-operator” Kubernetesa** (rozmawiasz z klastrem). AI dla Terraform to **„AI-programista” infrastruktury** (pisze kod, który potem przechodzi normalny proces review → plan → apply). W obu przypadkach kluczowe jest to samo: **AI generuje, a narzędzia walidujące i człowiek sprawdzają.**

---

## 1. Podstawy: generowanie konfiguracji z AI

### Dlaczego AI dobrze pisze konfigurację?

YAML Kubernetesa i HCL Terraforma to **deklaratywne, powtarzalne formaty**, których w danych treningowych modeli jest bardzo dużo. Dlatego AI świetnie radzi sobie z:
- generowaniem szkieletów (Deployment + Service + Ingress, VPC + EKS + node group),
- „tłumaczeniem” (docker-compose → manifesty K8s, CloudFormation → Terraform),
- refaktoryzacją (wydzielenie modułu, dodanie tagów do wszystkich zasobów),
- wyjaśnianiem cudzej konfiguracji.

### Dlaczego AI popełnia tu groźne błędy?

| Typowy błąd AI | Przykład |
|---|---|
| **Nieaktualne API / atrybuty** | `apiVersion: extensions/v1beta1` dla Ingress; atrybuty providera AWS usunięte kilka wersji temu (np. `acl` w `aws_s3_bucket`) |
| **Halucynacje** | Nieistniejący argument zasobu, nieistniejąca flaga `kubectl`, wymyślony moduł z Registry |
| **Niebezpieczne domyślne ustawienia** | Security group `0.0.0.0/0` na porcie 22, publiczny bucket S3, kontener jako root, brak limitów zasobów, `privileged: true` |
| **Brak dobrych praktyk** | Brak przypiętych wersji providerów i obrazów (`:latest`), brak remote state z blokadą, sekrety wpisane wprost w kod |
| **Niezrozumienie kontekstu** | Wygenerowany kod nie pasuje do konwencji, modułów i nazewnictwa w firmie |

### Złota zasada: pipeline weryfikacji

```
 AI generuje  →  format/lint  →  walidacja schematu  →  skan bezpieczeństwa  →  podgląd zmian  →  review człowieka  →  apply
              │                │                      │                      │                  │
 K8s:         │  yamllint      │  kubeconform         │  trivy config        │  kubectl diff    │  PR + approve
              │                │  --dry-run=server    │  kube-linter         │                  │
 Terraform:   │  terraform fmt │  terraform validate  │  trivy config        │  terraform plan  │  PR + approve
              │  tflint        │                      │  checkov             │                  │  (+ polityki OPA/Sentinel)
```

Im więcej konfiguracji generuje AI, tym **ważniejsze stają się automatyczne bramki**. To dokładnie strategia, którą HashiCorp ogłosił we wrześniu 2026: *„agent proponuje zmianę, a Terraform (polityki, plan, audyt) nią zarządza”*.

---

## 2. Do czego służą?

### 2.1 kubectl-ai

Open-source'owy (Apache 2.0) agent AI dla Kubernetesa od Google Cloud Platform, ok. 7,6 tys. gwiazdek na GitHubie. Działa jak **Claude Code wyspecjalizowany w Kubernetesie**: dostaje polecenie, sam uruchamia `kubectl` (i `bash`), analizuje wyniki i działa dalej w pętli.

Typowe zastosowania:
- **Generowanie manifestów:** „stwórz Deployment nginx z 3 replikami, limitami zasobów i Service typu ClusterIP”.
- **Operacje:** „przeskaluj deployment cart do 5 replik”, „pokaż logi z poda, który się restartuje”.
- **Diagnostyka:** „dlaczego pod payment jest w stanie Pending?”.
- **Wyjaśnianie:** `cat error.log | kubectl-ai "wyjaśnij ten błąd"`.

Ważne cechy:
- **Pyta o zgodę przed komendami modyfikującymi** zasoby (chyba że użyjesz `--skip-permissions`, czego nie rób).
- Tryb interaktywny (z sesjami, które można wznawiać) i jednorazowy (`--quiet`).
- Wiele dostawców LLM, w tym **AWS Bedrock** i lokalne modele (Ollama, llama.cpp).
- **Tryb serwera MCP** (`--mcp-server`): udostępnia narzędzia Kubernetesa innym asystentom (Claude Code, Copilot). Tryb **klienta MCP** (`--mcp-client`) pozwala z kolei korzystać z zewnętrznych serwerów MCP.
- Własne narzędzia w `~/.config/kubectl-ai/tools.yaml` (np. `helm`, `kustomize`, `aws`).
- **k8s-bench**: benchmark porównujący skuteczność modeli w zadaniach Kubernetesowych. Przydaje się przy wyborze modelu.

### 2.2 AI dla Terraform

**A. GitHub Copilot (lub inny asystent) w edytorze**
- **Podpowiedzi w locie** podczas pisania `.tf`.
- **Copilot Chat / Agent mode** w VS Code: „dodaj moduł EKS z dwoma node groupami w prywatnych podsieciach”. Agent sam edytuje pliki, uruchamia `terraform validate`/`plan` i poprawia błędy.
- **Copilot coding agent**: przypisujesz issue do Copilota, a on otwiera PR ze zmianą Terraform.
- **Copilot code review**: AI komentuje PR-y z IaC.
- **Własne instrukcje** (`.github/copilot-instructions.md`): firmowe standardy, np. „zawsze tagi `Owner` i `CostCenter`, zawsze moduły z naszego prywatnego Registry”.

**B. Terraform MCP Server (HashiCorp, GA 1.0)**
Rozwiązuje największy problem AI w Terraformie, czyli **nieaktualną wiedzę o providerach**. Serwer daje asystentowi narzędzia do:
- wyszukiwania providerów, zasobów i ich **aktualnej dokumentacji** w Terraform Registry,
- wyszukiwania i pobierania szczegółów **modułów** (publicznych i z prywatnego Registry w HCP Terraform),
- przeglądania **polityk** (Sentinel/OPA),
- operacji na **workspace'ach i runach** w HCP Terraform / Terraform Enterprise (tworzenie, aktualizacja, uruchamianie planu). Domyślnie są wyłączone i wymagają jawnego włączenia.

Działa z GitHub Copilot, Claude Code, Cursorem, IBM Bob i innymi klientami MCP.

**C. HCP Terraform: funkcje AI (opcjonalnie, płatne)**
- **HCP Terraform powered by Infragraph**: graf całej infrastruktury (własność, błędy konfiguracji, zależności) jako kontekst dla agentów AI. Od 2026 w *limited availability* dla planów Standard/Premium, tylko instancje US.
- **`tfctl`**: CLI dla HCP Terraform zaprojektowane także dla agentów AI (dry-run, odkrywanie schematów, zabezpieczenia przed operacjami niszczącymi).
- Kontrola przez **polityki jako kod**, **tożsamości per projekt** i **krótkotrwałe poświadczenia OIDC**.

---

## 3. Czym się różnią?

| Wymiar | kubectl-ai | Copilot + Terraform MCP |
|---|---|---|
| **Obiekt pracy** | Żywy klaster (imperatywnie) + generowane YAML-e | Kod w repozytorium (deklaratywnie) |
| **Moment ryzyka** | **Natychmiast**: komenda wykonana na klastrze | **Odroczony**: dopiero `apply` zmienia infrastrukturę, a wcześniej jest review i `plan` |
| **Ślad zmian** | Historia sesji kubectl-ai (zmiany na klastrze omijają Git, chyba że generujesz pliki) | Git (PR, review, historia) + plan + audyt HCP Terraform |
| **Pętla agenta** | Tak: wykonuje `kubectl` i analizuje wynik | Tak (agent mode): edytuje pliki i uruchamia `validate`/`plan` |
| **Źródło aktualnej wiedzy** | Stan klastra (`kubectl explain`, `api-resources`) | Terraform Registry przez MCP |
| **Wybór modelu** | Dowolny (w tym Bedrock i lokalne) | Copilot: lista modeli GitHuba; przez MCP: dowolny asystent |
| **Najlepsze do** | Szybkie operacje i diagnostyka, prototypy manifestów, nauka K8s | Budowa i utrzymanie IaC w zespole, standardy firmowe |
| **Pasuje do GitOps?** | Tylko w trybie „generuj plik, nie stosuj” | Tak, naturalnie |

**Ważne rozróżnienie dla uczestników:** w podejściu **GitOps / IaC** (ArgoCD, Flux, Terraform w CI) zmiany robione przez kubectl-ai bezpośrednio na klastrze to **dryf konfiguracji**: ArgoCD je nadpisze, a nikt nie będzie wiedział, co się stało. Dlatego na środowiskach zarządzanych przez GitOps używaj kubectl-ai do **diagnozy i generowania plików**, a zmiany wprowadzaj przez PR.

---

## 4. Jaką mają opinię?

### kubectl-ai

**Plusy:**
- Szybko zdobył popularność (projekt Google, prosty start, `kubectl krew install ai`).
- Chwalony za **wygodę w codziennych operacjach** i dla osób uczących się Kubernetesa („nie muszę pamiętać `jsonpath`”).
- **Elastyczność modeli**: także lokalne i Bedrock, co ma znaczenie w firmach.
- Tryb MCP pozwala używać go jako „wtyczki Kubernetes” do innych asystentów.
- Bezpieczne domyślne ustawienie: pyta przed zmianami.

**Minusy:**
- **Projekt społecznościowy**, oficjalnie niewspierany przez Google. Dynamiczny rozwój oznacza zmieniające się flagi i zachowanie.
- Jakość zależy mocno od modelu. Małe lokalne modele często się mylą (stąd *tool-use shim*).
- Konkurencja jest silna: Claude Code lub Copilot z serwerem MCP Kubernetesa robią to samo i więcej. Część osób uważa wyspecjalizowane CLI za zbędne.
- Ryzyko „klikania Enter” przy prośbach o zgodę, czyli zmęczenie akceptacjami.

### AI dla Terraform (Copilot + MCP)

**Plusy:**
- Copilot bardzo przyspiesza pisanie **powtarzalnego HCL** (zmienne, outputy, tagi, bloki `dynamic`).
- **Terraform MCP Server** wyraźnie zmniejsza halucynacje: AI sprawdza aktualne argumenty zasobu zamiast „pamiętać” sprzed roku. To najczęściej podkreślana zaleta.
- Agent mode z `terraform validate`/`plan` w pętli sam naprawia błędy składni i typów.
- Ekosystem i kierunek (HCP Terraform jako „control plane” dla agentów) wyglądają dojrzale.

**Minusy:**
- Bez MCP Copilot **często generuje przestarzałe konstrukcje** providera AWS (szczególnie po dużych wersjach, np. 5.x → 6.x).
- Generuje kod **działający, ale niezgodny z firmowymi standardami**. Pomagają instrukcje i prywatne Registry.
- **Bezpieczeństwo:** AI chętnie upraszcza (otwarte security groups, szerokie polityki IAM `"*"`). Wymaga skanerów (Trivy, Checkov).
- Funkcje AI w HCP Terraform (Infragraph) są **płatne, w limited availability i tylko w regionie US**. W Europie na razie mało praktyczne.
- Model cenowy Copilota stał się bardziej złożony: od czerwca 2026 intensywne użycie agenta jest liczone w kredytach / premium requests ponad cenę bazową.

---

## 5. Czy są bezpieczne?

### 5.1 kubectl-ai

| Ryzyko | Mitygacja |
|---|---|
| **Wykonanie destrukcyjnej komendy** (`delete`, `scale 0`, `patch`) | Nigdy nie używaj `--skip-permissions`. Czytaj każdą komendę przed akceptacją |
| **Uprawnienia = Twój kubeconfig** (jeśli jesteś cluster-adminem, agent też nim jest) | Osobny kontekst z **ServiceAccountem read-only** do diagnozy; zmiany przez GitOps |
| **Dane klastra wysyłane do LLM** (nazwy, YAML-e, logi, potencjalnie zawartość ConfigMap/Secret, jeśli agent je odczyta) | RBAC bez `get secrets`; model w firmowym tenancie (**AWS Bedrock** w Twoim koncie, Azure OpenAI), przez firmowe proxy (np. LiteLLM z budżetami i logiem) albo lokalny (Ollama) |
| **Prompt injection** (np. złośliwa adnotacja albo log poda z instrukcją dla agenta) | Read-only przy analizie niezaufanych danych, akceptacja przed zmianami |
| **Dryf względem GitOps** | Generuj pliki do repo zamiast `kubectl apply` |
| **Tryb MCP server wystawiony w sieci** | Tylko stdio lokalnie albo HTTP z uwierzytelnieniem (OAuth 2.1), nigdy publicznie |

### 5.2 AI dla Terraform

| Ryzyko | Mitygacja |
|---|---|
| **Niebezpieczna konfiguracja** (publiczny S3, `0.0.0.0/0`, IAM `*`) | `trivy config`, `checkov`, polityki OPA/Sentinel w CI jako **blokujące** bramki |
| **Sekrety w kodzie** generowanym przez AI | Push protection (GHAS), `trivy fs --scanners secret`, zmienne/Secrets Manager zamiast stringów |
| **Plik stanu (`terraform.tfstate`) zawiera sekrety** | **Nigdy nie dawaj AI dostępu do stanu ani nie wklejaj go do czatu**. Dodaj do `.gitignore`, `.copilotignore` i ustawień ignorowania asystenta |
| **AI wykonujące `apply`** | Agent może robić `validate`/`plan`; `apply` tylko przez CI po akceptacji PR |
| **Za szerokie poświadczenia chmurowe w terminalu agenta** | Rola IAM read-only do `plan` (lub `plan` tylko w CI z OIDC), osobne konta AWS dla dev i prod |
| **Terraform MCP z `ENABLE_TF_OPERATIONS`** | Domyślnie wyłączone; włączaj świadomie, z tokenem o minimalnym zakresie (team token / project-scoped) |
| **Kod wysyłany do dostawcy AI** | Copilot Business/Enterprise: kod nie jest używany do trenowania; polityki organizacji (wykluczanie plików, wybór modeli) |
| **Halucynowane moduły** (np. nieistniejący moduł o nazwie podobnej do prawdziwego, czyli ryzyko *typosquattingu*) | Tylko moduły z zaufanych źródeł (prywatne Registry, zweryfikowani autorzy), przypinanie wersji |

---

## 6. Licencje i koszty

| Element | Licencja | Koszt |
|---|---|---|
| **kubectl-ai** | Apache 2.0 | 0 zł + tokeny LLM (Gemini/OpenAI/Bedrock wg cennika dostawcy; Ollama za darmo) |
| **Terraform MCP Server** | MPL-2.0 | 0 zł |
| **Terraform CLI** | BUSL 1.1 (od 2023; darmowy w normalnym użyciu, ograniczenie dotyczy budowy konkurencyjnych produktów) | 0 zł. Alternatywa w pełni open source: **OpenTofu** (MPL-2.0) |
| **GitHub Copilot Free** | — | 0 zł: limit podpowiedzi i wiadomości czatu, 50 premium requests/mies. |
| **Copilot Pro / Pro+** | — | 10 / 39 USD miesięcznie (indywidualnie) |
| **Copilot Business / Enterprise** | — | 19 / 39 USD na użytkownika miesięcznie (polityki, audyt, wykluczenia treści); intensywne użycie agenta liczone dodatkowo w kredytach |
| **HCP Terraform** | SaaS | plan Free (limit zasobów), Standard / Premium płatne; **Infragraph tylko Standard/Premium, region US** |

**Na szkolenie (AWS):**
- **kubectl-ai:** darmowy. Model przez **LiteLLM proxy** w klastrze szkoleniowym (`https://llm.aiops.marniok.dev`, namespace `ai`), tak jak k8sgpt: każdy uczestnik ma własny klucz wirtualny z budżetem 5 USD, a klucz Anthropic zostaje w klastrze. Bedrocka na szkoleniu nie używamy (limit 10 RPM na konto nie wystarczy dla grupy).
- **Terraform:** Copilot Free wystarczy do pokazania podstaw. Do agent mode na większą skalę Copilot Pro (lub trial) albo **Claude Code z Terraform MCP Server**, którego uczestnicy już znają.
- **Terraform MCP Server:** darmowy, działa bez konta HCP Terraform (sam publiczny Registry).

---

## 7. Instalacja i użycie

### 7.1 kubectl-ai: instalacja

```bash
# Opcja 1: krew (plugin kubectl), potem uruchamiasz jako `kubectl ai`
kubectl krew install ai

# Opcja 2: Homebrew (jeśli dostępne) albo plik binarny z wydań na GitHubie
# https://github.com/GoogleCloudPlatform/kubectl-ai/releases/latest

# Opcja 3: skrypt instalacyjny. Przed uruchomieniem przeczytaj jego treść! (patrz lekcja z Trivy)
curl -sSL https://raw.githubusercontent.com/GoogleCloudPlatform/kubectl-ai/main/install.sh -o install.sh
less install.sh && bash install.sh

kubectl-ai version
```

### 7.2 kubectl-ai: konfiguracja modelu

```bash
# Gemini (domyślny dostawca)
export GEMINI_API_KEY="..."
kubectl-ai

# OpenAI
export OPENAI_API_KEY="sk-..."
kubectl-ai --llm-provider=openai --model=gpt-5.5

# NA SZKOLENIU: LiteLLM proxy (endpoint zgodny z OpenAI) — klucz wirtualny uczestnika
export OPENAI_ENDPOINT="https://llm.aiops.marniok.dev/v1"
export OPENAI_API_KEY="sk-..."          # klucz LiteLLM z karty uczestnika, nie klucz Anthropic
kubectl-ai --llm-provider=openai --model=claude-haiku-4-5 --enable-tool-use-shim
# trudniejsze zadania: --model=claude-sonnet-5-5 (droższy, zjada budżet szybciej)

# W firmie, alternatywa: AWS Bedrock — dane zostają w koncie AWS
# Uwierzytelnienie standardowo: AWS SSO / profil / rola IAM; region z dostępem do modelu
export AWS_PROFILE=szkolenie AWS_REGION=eu-central-1
aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId'   # ID modeli
kubectl-ai --llm-provider=bedrock --model=<inference-profile-id-modelu-claude>

# Lokalnie: Ollama (bez kosztów i bez wysyłania danych)
ollama pull qwen3
kubectl-ai --llm-provider=ollama --model=qwen3 --enable-tool-use-shim
```

Plik konfiguracyjny `~/.config/kubectl-ai/config.yaml`:

```yaml
llmProvider: openai             # LiteLLM udaje API OpenAI; endpoint i klucz z OPENAI_ENDPOINT / OPENAI_API_KEY
model: claude-haiku-4-5
skipPermissions: false        # NIGDY true na współdzielonym/produkcyjnym klastrze
maxIterations: 20
toolConfigPaths: ~/.config/kubectl-ai/tools.yaml
```

**Jak to działa z LiteLLM:** kubectl-ai wysyła zapytania w formacie OpenAI (z wywołaniami narzędzi), a LiteLLM tłumaczy je na API Anthropic i z powrotem. Niestandardowe parametry próbkowania, których modele nie przyjmują, LiteLLM wycina (`additional_drop_params` w konfiguracji modelu w bramie).


### 7.3 kubectl-ai: przykłady użycia

```bash
# Tryb interaktywny (meta-komendy: models, tools, reset, clear, exit)
kubectl-ai
>>> Pokaż pody w namespace shop, które się restartują, i wyjaśnij dlaczego
>>> Wygeneruj manifest Deployment dla obrazu nginx:1.27 z 3 replikami, limitami CPU/RAM,
    probe'ami i securityContext (non-root, readOnlyRootFilesystem). NIE stosuj go — zapisz do pliku nginx.yaml

# Tryb jednorazowy
kubectl-ai --quiet "który node ma najwięcej podów w stanie Pending?"

# Przekazanie danych przez stdin
kubectl logs deploy/cart -n shop --tail=200 | kubectl-ai --quiet "znajdź przyczynę błędów w tych logach"
kubectl get events -n shop -o yaml | kubectl-ai --quiet "podsumuj, co się działo w ostatniej godzinie"

# Sesje (kontekst między uruchomieniami)
kubectl-ai --new-session
kubectl-ai --list-sessions
kubectl-ai --resume-session <id>
```

Gdy kubectl-ai chce wykonać zmianę, pyta o zgodę:

```
  The following command will modify resources:
    kubectl scale deployment cart --replicas=5 -n shop
  Do you want to proceed? (yes / yes, and don't ask again / no)
```

**Zawsze czytaj komendę przed akceptacją.** Opcji „don't ask again” nie używaj na współdzielonych klastrach.

### 7.4 kubectl-ai jako serwer MCP (np. dla Claude Code)

```bash
claude mcp add kubectl-ai -- kubectl-ai --mcp-server
# Teraz w Claude Code: "Użyj kubectl-ai, żeby sprawdzić stan namespace shop"
```

### 7.5 Weryfikacja wygenerowanych manifestów (obowiązkowo)

```bash
# Schemat (offline, zgodność z wersją K8s klastra)
kubeconform -strict -summary -kubernetes-version 1.33.0 nginx.yaml

# Walidacja przez API serwera (admission, CRD, polityki) bez wprowadzania zmian
kubectl apply --dry-run=server -f nginx.yaml

# Co by się zmieniło względem stanu klastra
kubectl diff -f nginx.yaml

# Dobre praktyki i bezpieczeństwo
trivy config nginx.yaml
kube-linter lint nginx.yaml
```

### 7.6 Terraform + GitHub Copilot: konfiguracja

1. VS Code + rozszerzenia **GitHub Copilot** (Chat) i **HashiCorp Terraform**.
2. Zaloguj się do GitHuba (plan Free wystarczy na start).
3. Dodaj instrukcje dla Copilota w repo (`.github/copilot-instructions.md`):

```markdown
# Standardy Terraform w tym repozytorium
- Provider AWS w wersji ~> 6.0, Terraform >= 1.10; zawsze blok required_providers z przypiętą wersją.
- Region domyślny eu-central-1; remote state w S3 z blokadą (use_lockfile = true).
- Każdy zasób ma tagi przez default_tags: Owner, Project, Environment, CostCenter.
- Preferuj moduły terraform-aws-modules/* z przypiętą wersją; nie twórz VPC ręcznie.
- Bezpieczeństwo: brak 0.0.0.0/0 na portach innych niż 80/443 na ALB; S3 zawsze z blokadą publicznego dostępu
  i szyfrowaniem; polityki IAM bez "*" w Action i Resource; sekrety tylko z AWS Secrets Manager.
- Po każdej zmianie: terraform fmt, terraform validate, tflint. Nigdy nie uruchamiaj terraform apply.
```

4. Wykluczenie wrażliwych plików z kontekstu AI: `.gitignore` dla `*.tfstate*`, `.terraform/`, `*.tfvars` z sekretami. W Copilot Business/Enterprise dodatkowo **content exclusion** w ustawieniach organizacji.

### 7.7 Terraform MCP Server: instalacja

**Dla Claude Code:**

```bash
claude mcp add terraform -- docker run -i --rm hashicorp/terraform-mcp-server
```

**Dla VS Code / GitHub Copilot** (`.vscode/mcp.json`):

```json
{
  "servers": {
    "terraform": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "hashicorp/terraform-mcp-server"]
    }
  }
}
```

Opcjonalnie, dla HCP Terraform (prywatne Registry, workspace'y):

```json
{
  "servers": {
    "terraform": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "TFE_TOKEN", "-e", "TFE_ADDRESS", "hashicorp/terraform-mcp-server"],
      "env": {
        "TFE_TOKEN": "${input:tfe_token}",
        "TFE_ADDRESS": "https://app.terraform.io"
      }
    }
  }
}
```

> Operacje zmieniające (tworzenie workspace'ów, runy) wymagają dodatkowo `ENABLE_TF_OPERATIONS=true`. **Na szkoleniu ich nie włączaj.**

Bez Dockera: `go install github.com/hashicorp/terraform-mcp-server/cmd/terraform-mcp-server@latest`.

### 7.8 Terraform z AI: przykładowe prompty (agent mode / Claude Code)

```
Używając Terraform MCP, sprawdź aktualną dokumentację zasobu aws_s3_bucket i powiązanych zasobów,
a następnie utwórz moduł ./modules/secure-bucket: szyfrowanie KMS, wersjonowanie, blokada publicznego
dostępu, lifecycle do Glacier po 90 dniach. Dodaj variables.tf, outputs.tf i README.

Znajdź w Terraform Registry najnowszą wersję modułu terraform-aws-modules/eks/aws i przygotuj
konfigurację klastra EKS 1.33 z managed node group (t3.large, 2–4 węzły) w prywatnych podsieciach
istniejącego VPC (dane z data source po tagu Name=lab-vpc).

Przejrzyj katalog ./infra i wskaż: przestarzałe atrybuty providera AWS, brakujące tagi,
zasoby bez szyfrowania i reguły security group otwarte na świat. Zaproponuj poprawki jako diff.

Przepisz ten docker-compose.yml na manifesty Kubernetes (Deployment, Service, ConfigMap)
oraz Terraform dla bazy RDS PostgreSQL, z której korzysta aplikacja.
```

### 7.9 Weryfikacja wygenerowanego Terraform (obowiązkowo)

```bash
terraform fmt -recursive
terraform init -backend=false
terraform validate

tflint --init && tflint --recursive          # błędy specyficzne dla providera AWS (np. zły typ instancji)
trivy config .                               # błędy konfiguracji / bezpieczeństwo
checkov -d .                                 # alternatywny/uzupełniający skaner polityk

terraform plan -out=tfplan                   # z rolą read-only
terraform show -json tfplan | conftest test - # opcjonalnie: polityki OPA na planie
```

W CI (GitHub Actions) te same kroki jako **blokujące** sprawdzenia PR. `apply` dopiero po akceptacji człowieka, najlepiej z rolą IAM przez OIDC.

---

## Źródła

**kubectl-ai**
- Repozytorium i dokumentacja: https://github.com/GoogleCloudPlatform/kubectl-ai
- k8s-bench: https://github.com/GoogleCloudPlatform/kubectl-ai/tree/main/k8s-bench

**Terraform i AI**
- Terraform MCP Server (GA): https://www.hashicorp.com/en/blog/terraform-mcp-server-is-now-generally-available
- Terraform MCP Server (repozytorium): https://github.com/hashicorp/terraform-mcp-server
- HCP Terraform powered by Infragraph (limited availability): https://www.hashicorp.com/en/blog/hcp-terraform-powered-by-infragraph-limited-availability-launch
- HCP Terraform jako control plane dla AI (InfoQ, 09.2026): https://www.infoq.com/news/2026/09/hcp-terraform-ai-driven-control/
- HashiConf 2025: Project Infragraph: https://www.hashicorp.com/en/blog/scale-infrastructure-with-new-terraform-and-packer-features-at-hashiconf-2025

**GitHub Copilot**
- Plany i cennik: https://github.com/features/copilot/plans
- Instrukcje repozytorium dla Copilota: https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot
- MCP w VS Code: https://code.visualstudio.com/docs/copilot/chat/mcp-servers

**Walidacja**
- kubeconform: https://github.com/yannh/kubeconform
- kube-linter: https://github.com/stackrox/kube-linter
- tflint: https://github.com/terraform-linters/tflint
- Checkov: https://www.checkov.io
