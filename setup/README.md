# Przygotowanie stanowiska

Szkolenie trwa codziennie **9:00–17:00**, przerwy: 10:45–11:00, obiad 13:00–13:30, 15:00–15:15. Narzędzia i krok 0 zrób przed szkoleniem. Resztę robimy razem w dniu 1:

| Kiedy | Kroki |
|---|---|
| przed szkoleniem | narzędzia na laptopie, 0. fork i klon repo |
| 9:00, na start | 1. adres IP na czat; dostajesz kartę dostępową |
| przed przerwą 10:45, razem | 2. klaster, 3. Twoja Kantyna, 4. Claude Code, 5. k8sgpt |

Dane dostępowe są na Twojej **karcie dostępowej** (dostaniesz ją prywatnie na czacie). Nie wklejaj ich do repo ani do czatu z modelem.

## Narzędzia na laptopie

Zainstaluj przed szkoleniem. Windows: wszystko w WSL2 (Ubuntu), łącznie z gitem i Claude Code.

| Narzędzie | macOS | Linux / WSL | Sprawdzenie |
|---|---|---|---|
| git | `brew install git` | `sudo apt install git` | `git --version` |
| aws CLI v2 | `brew install awscli` | niżej | `aws --version` → `aws-cli/2.…` |
| kubectl | `brew install kubectl` | niżej | `kubectl version --client` |
| Claude Code | `curl -fsSL https://claude.ai/install.sh \| bash` | to samo | `claude --version` |

Linux / WSL (x86_64):

```bash
# aws CLI v2
curl -o awscliv2.zip https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
unzip -q awscliv2.zip && sudo ./aws/install && rm -rf aws awscliv2.zip
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/ && rm kubectl
```

k8sgpt instalujemy razem w dniu 1 (krok 5).

## 0. Twoja kopia repo (fork)

Na szkoleniu każdy pracuje we własnym forku: tam zapisujesz swoją pracę, w lab03 uruchamiasz w nim pipeline (GitHub Actions), a po szkoleniu repo zostaje Twoje.

Potrzebujesz dwóch rzeczy:
- **git** na laptopie (tabela wyżej),
- **konto GitHub**: jeśli go nie masz, załóż je przed szkoleniem: https://github.com/signup.

1. Otwórz https://github.com/dawid-marniok/aiops-praktyka → przycisk **Fork** (prawy górny róg) → **Create fork**.
2. Sklonuj **swój** fork i podłącz repo prowadzącego jako `upstream`:
   ```bash
   git clone https://github.com/<twoj-login-github>/aiops-praktyka.git
   cd aiops-praktyka
   git remote add upstream https://github.com/dawid-marniok/aiops-praktyka.git
   git config pull.rebase false
   ```

Git pyta przy commicie, kim jesteś? Raz: `git config --global user.name "Imię Nazwisko"` i `git config --global user.email "adres@firma.pl"`.

### Każdego dnia o 9:00

```bash
git add -A && git commit -m "moja praca"   # najpierw zapisz swoje zmiany (jeśli są)
git pull upstream main                      # pobierz nowe laby i materiały
git push                                    # wypchnij wszystko do swojego forka
```

## 1. Adres IP

O 9:00 wklej na czat wynik:

```bash
curl -4 ifconfig.me
```

Bez tego nie działa brama AI (LiteLLM), Grafana ani adres Twojej Kantyny. Zmieniasz sieć albo VPN → podaj nowy adres.

## 2. Konsola AWS i klaster

Logujesz się przez przeglądarkę loginem i hasłem do konsoli AWS z karty. Przy okazji masz otwartą konsolę AWS: zobaczysz tam klaster EKS i usługi szkolenia.

```bash
aws --version                              # potrzebne aws-cli ≥ 2.32; starsze zaktualizuj
aws configure set region eu-central-1 --profile aiops
aws login --profile aiops                  # przeglądarka: login i hasło z karty
aws eks update-kubeconfig --name aiops --region eu-central-1 --profile aiops --alias aiops
kubectl config set-context aiops --namespace <login>
kubectl get pods
```

Sesja wygasła (`kubectl` albo `aws` zgłasza błąd logowania)? Ponów `aws login --profile aiops`. Gdy `aws login` w ogóle nie działa, użyj planu B z karty (klucze dostępowe).

## 3. Twoja Kantyna

```bash
setup/check.sh          # z katalogu repo → SUKCES: 11/11
```

W przeglądarce: `https://<login>.aiops.marniok.dev`

## 4. Claude Code

```bash
claude        # w katalogu repo
/status       # musi pokazać konto szkoleniowe uczNN@sages.io
```

Wyjdź z Claude Code (`/exit`) i pobierz najnowsze laby: `git pull upstream main`.

Prywatne konto albo `ANTHROPIC_API_KEY` w profilu powłoki → `/logout`, zaloguj się kontem szkoleniowym.

## 5. k8sgpt

Instalacja:

```bash
brew install k8sgpt                    # macOS
# Linux / WSL:
curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.39/k8sgpt_$(dpkg --print-architecture).deb
sudo dpkg -i k8sgpt_*.deb && rm k8sgpt_*.deb
k8sgpt version                         # ≥ 0.4.39
```

Konfiguracja (klucz z karty):

```bash
k8sgpt auth add --backend litellm --baseurl https://llm.aiops.marniok.dev/v1 \
  --model claude-haiku-4-5 --password <klucz-LiteLLM-z-karty>
k8sgpt auth default --provider litellm
k8sgpt analyze --namespace <login>
```

## Dzień 2: narzędzia

Zainstaluj rano w dniu 2, przed lab03.

| Narzędzie | Do czego | macOS | Sprawdzenie |
|---|---|---|---|
| gh | lab03 | `brew install gh` | `gh --version` |
| actionlint | lab03 | `brew install actionlint` | `actionlint --version` |
| zizmor | lab03 | `brew install zizmor` | `zizmor --version` |
| trivy | lab04 | `brew install trivy` | `trivy --version` → **nie** 0.69.4–0.69.6 |
| terraform | lab04 | `brew install hashicorp/tap/terraform` | `terraform version` → ≥ 1.16 |
| kubectl-ai | lab04 | `brew install kubectl-ai` | `kubectl-ai version` |

Linux / WSL (x86_64):

```bash
sudo apt install -y gh unzip
# actionlint
curl -fsSL https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz | tar xz actionlint
sudo install actionlint /usr/local/bin/ && rm actionlint
# zizmor
curl -fsSL https://github.com/zizmorcore/zizmor/releases/download/v1.30.1/zizmor-x86_64-unknown-linux-gnu.tar.gz | tar xz zizmor
sudo install zizmor /usr/local/bin/ && rm zizmor
# trivy
curl -fsSLO https://github.com/aquasecurity/trivy/releases/download/v0.75.0/trivy_0.75.0_Linux-64bit.deb
sudo dpkg -i trivy_0.75.0_Linux-64bit.deb && rm trivy_0.75.0_Linux-64bit.deb
# terraform
curl -fsSLO https://releases.hashicorp.com/terraform/1.16.5/terraform_1.16.5_linux_amd64.zip
unzip -o terraform_1.16.5_linux_amd64.zip terraform && sudo install terraform /usr/local/bin/ && rm terraform terraform_1.16.5_linux_amd64.zip
# kubectl-ai
curl -fsSL https://github.com/GoogleCloudPlatform/kubectl-ai/releases/download/v0.0.31/kubectl-ai_Linux_x86_64.tar.gz | tar xz kubectl-ai
sudo install kubectl-ai /usr/local/bin/ && rm kubectl-ai
```

Logowanie do GitHuba (lab03):

```bash
gh auth login        # GitHub.com → HTTPS → przeglądarka
gh auth status
```

kubectl-ai (lab04) łączy się z bramą AI szkolenia. Klucz jest ten sam co w k8sgpt:

```bash
export OPENAI_API_KEY=<klucz-LiteLLM-z-karty>
export OPENAI_ENDPOINT=https://llm.aiops.marniok.dev/v1
kubectl-ai --llm-provider=openai --model=claude-haiku-4-5 --enable-tool-use-shim --quiet "ile podów jest w moim namespace?"
```

## Adresy

| Co | Adres |
|---|---|
| Twoja Kantyna | `https://<login>.aiops.marniok.dev` |
| Brama AI (LiteLLM) | `https://llm.aiops.marniok.dev/v1` |
| Grafana | `https://grafana.aiops.marniok.dev` |

Budżet klucza LiteLLM jest ograniczony. Komunikat `budget exceeded` → zgłoś prowadzącemu. Po szkoleniu dostęp do klastra, kont Claude i kluczy LiteLLM wygasa. Repo zostaje Twoje.
