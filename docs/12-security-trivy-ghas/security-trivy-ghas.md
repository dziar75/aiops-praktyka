# Security AI — Trivy i GitHub Advanced Security

Materiał pomocniczy do szkolenia „AIOps w praktyce”. Diagram architektury: [`architektura.html`](architektura.html).

> Stan na 1 października 2026. Sprawdź linki w sekcji Źródła, zanim z nich skorzystasz, bo cenniki GitHuba i wersje Trivy zmieniają się często.
>
> ⚠️ **Ważne:** w marcu 2026 Trivy padł ofiarą **ataku na łańcuch dostaw** (CVE-2026-33634): złośliwy kod w oficjalnych wydaniach i GitHub Actions kradł sekrety z pipeline'ów. Opis w sekcji 4. To aktualny case study. **Przed labem upewnij się, że używasz bezpiecznych wersji** (`trivy --version`).

---

## TL;DR

| | **Trivy** | **GitHub Advanced Security (GHAS)** |
|---|---|---|
| **Jednym zdaniem** | Darmowy, uniwersalny skaner bezpieczeństwa (obrazy, kod, IaC, K8s, SBOM) | Platforma bezpieczeństwa wbudowana w GitHuba: analiza kodu, sekrety, zależności + AI do naprawy |
| **Gdzie jest AI?** | **Sam skaner nie używa AI** (reguły i bazy CVE). AI wchodzi przez **Trivy MCP Server** (asystent AI uruchamia skany i tłumaczy wyniki) oraz integrację z k8sgpt | **Wbudowane**: Copilot Autofix (propozycje poprawek), AI do wykrywania haseł (generic secrets), AI security detections w PR, skanowanie sekretów w agentach AI przez GitHub MCP |
| **Co skanuje** | Obrazy kontenerów, system plików, repozytoria, IaC (Terraform, K8s YAML, Helm, Dockerfile, CloudFormation), klaster K8s, SBOM, licencje, sekrety | Kod źródłowy (CodeQL), sekrety w historii repo, zależności (Dependabot), PR-y |
| **Gdzie działa** | CLI, CI/CD, operator w klastrze, IDE | Tylko GitHub (github.com, GitHub Enterprise Server) |
| **Licencja** | Apache 2.0, **darmowy** | **Darmowy dla repozytoriów publicznych**; dla prywatnych płatny: Secret Protection 19 USD + Code Security 30 USD za aktywnego committera / mies. |
| **Najlepsze dla** | Skanowanie obrazów i IaC w każdym CI; bezpieczeństwo K8s | Zespoły na GitHubie, które chcą „security w PR-ach” z automatycznymi poprawkami |

**Najkrócej:** Trivy **znajduje** podatności i błędy konfiguracji wszędzie (darmowo). GHAS **znajduje i pomaga naprawić** problemy w kodzie na GitHubie (płatnie dla repo prywatnych). Narzędzia świetnie się łączą: wyniki Trivy można wysłać do zakładki *Security* w GitHubie (format SARIF).

---

## 1. Podstawy: czym jest „Security AI” w DevOps

Klasyczne narzędzia bezpieczeństwa działają **regułowo**: baza znanych podatności (CVE), wzorce sekretów (np. `AKIA...` dla kluczy AWS), reguły konfiguracji („kontener nie powinien działać jako root”). Są szybkie i powtarzalne, ale:
- generują **dużo alertów**, z których wiele jest nieistotnych,
- nie mówią, **jak naprawić** problem w Twoim konkretnym kodzie,
- nie wykrywają tego, czego nie opisuje żadna reguła (np. hasło `Zima2026!` wpisane w kod).

AI dokłada trzy rzeczy:

| Rola AI | Przykład |
|---|---|
| **Naprawa** | Copilot Autofix: „CodeQL znalazł SQL injection, a tu jest gotowa poprawka w PR” |
| **Wykrywanie tego, czego nie łapią reguły** | AI wykrywa hasła bez stałego wzorca; AI security detections dla języków nieobsługiwanych przez CodeQL |
| **Tłumaczenie i priorytetyzacja** | Asystent AI przez Trivy MCP: „Które z tych 230 CVE w obrazie naprawdę są ważne i co zrobić?” |

**Zasada niezmienna:** skaner (regułowy) wykrywa, AI pomaga zrozumieć i naprawić, **człowiek weryfikuje i akceptuje**.

### Słowniczek

| Pojęcie | Znaczenie |
|---|---|
| **CVE** | Identyfikator znanej podatności (np. CVE-2026-33634) |
| **SCA** (*Software Composition Analysis*) | Analiza zależności (bibliotek) pod kątem znanych podatności. Trivy, Dependabot |
| **SAST** (*Static Application Security Testing*) | Analiza kodu źródłowego bez uruchamiania. CodeQL w GHAS |
| **IaC scanning / misconfiguration** | Wykrywanie błędów konfiguracji w Terraformie, YAML-ach K8s, Dockerfile. Trivy |
| **Secret scanning** | Wykrywanie haseł, tokenów i kluczy w kodzie i historii Gita |
| **Push protection** | Blokada `git push`, jeśli commit zawiera sekret |
| **SBOM** (*Software Bill of Materials*) | „Lista składników” oprogramowania (CycloneDX, SPDX) |
| **SARIF** | Standardowy format wyników skanerów. GitHub go importuje |
| **Supply chain attack** | Atak przez zaufany element łańcucha dostaw (bibliotekę, akcję CI, obraz) |

---

## 2. Do czego służą?

### 2.1 Trivy (Aqua Security)

Najpopularniejszy open-source'owy skaner bezpieczeństwa w świecie kontenerów (projekt Aqua Security, Apache 2.0). Jeden plik binarny skanuje:

| Cel (*target*) | Komenda | Co wykrywa |
|---|---|---|
| **Obraz kontenera** | `trivy image nginx:1.27` | CVE w pakietach systemu i bibliotekach aplikacji, sekrety, błędy w Dockerfile |
| **System plików / projekt** | `trivy fs .` | CVE w zależnościach (package-lock, go.mod, requirements…), sekrety, IaC |
| **Repozytorium Git** | `trivy repo https://github.com/org/app` | j.w. dla zdalnego repo |
| **IaC** | `trivy config ./terraform` | Błędy konfiguracji: Terraform, CloudFormation, K8s YAML, Helm, Dockerfile, Azure ARM |
| **Klaster Kubernetes** | `trivy k8s --report summary` | Podatności obrazów, błędy konfiguracji zasobów, RBAC, zgodność z CIS / NSA |
| **SBOM** | `trivy image --format cyclonedx …` / `trivy sbom sbom.json` | Generowanie i skanowanie SBOM |

Dodatkowo:
- **Trivy Operator**: działa w klastrze i ciągle skanuje zasoby, a wyniki zapisuje jako CRD (`VulnerabilityReport`, `ConfigAuditReport`). Integruje się z Prometheusem i Grafaną.
- **Trivy MCP Server** (`trivy mcp`): udostępnia Trivy asystentom AI (Claude Code, Copilot w VS Code, Cursor, JetBrains). Możesz napisać: „przeskanuj ten projekt i powiedz, które podatności mają gotową poprawkę”, a asystent sam uruchomi Trivy i przeanalizuje wynik.
- **Integracja z k8sgpt**: `k8sgpt integration activate trivy` dodaje wyniki Trivy Operatora do analizy AI w k8sgpt (patrz `docs/03-k8sgpt/k8sgpt.md`).
- **Wersja komercyjna:** Aqua Platform (rozszerzone polityki, runtime security, AI) na bazie tego samego silnika.

### 2.2 GitHub Advanced Security (GHAS)

Zestaw funkcji bezpieczeństwa wbudowany w GitHuba. Od kwietnia 2025 sprzedawany jako **dwa osobne produkty**:

**GitHub Secret Protection** (sekrety):
- **Secret scanning**: skanowanie całej historii repo w poszukiwaniu tokenów (ponad 200 dostawców: AWS, Azure, Slack, OpenAI…). Część dostawców jest automatycznie powiadamiana i unieważnia token.
- **Push protection**: blokada pusha z sekretem, zanim trafi do repo.
- **Copilot secret scanning (AI)**: wykrywanie **„generycznych” sekretów** (haseł bez stałego wzorca) przez model AI. **Nie wymaga licencji Copilot.**
- **Własne wzorce** (custom patterns), także generowane przez AI z opisu.
- **Skanowanie sekretów w agentach AI** przez GitHub MCP Server (GA od maja 2026): agent sprawdza zmiany pod kątem sekretów przed commitem.

**GitHub Code Security** (kod i zależności):
- **Code scanning z CodeQL**: SAST dla m.in. Java, C#, JS/TS, Python, Go, Ruby, C/C++, Kotlin, Swift, Rust i GitHub Actions. Alerty bezpośrednio w PR.
- **AI security detections** (od lipca 2026 w PR): AI rozszerza code scanning na języki i frameworki, których CodeQL nie obsługuje (np. część IaC, skrypty).
- **Copilot Autofix (AI)**: dla alertu code scanning generuje **propozycję poprawki z wyjaśnieniem**, do akceptacji jednym kliknięciem w PR. Działa też dla alertów z zewnętrznych narzędzi (np. ESLint).
- **Security campaigns**: masowe naprawianie długu bezpieczeństwa. Wybierasz grupę alertów, Autofix generuje poprawki, przypisujesz to zespołom.
- **Dependency review** w PR, **Dependabot** (alerty i automatyczne PR-y z aktualizacjami). Dependabot alerts i security updates są dostępne **za darmo** dla wszystkich repo.
- Import wyników z **innych skanerów** przez SARIF, np. Trivy.

---

## 3. Czym się różnią?

| Wymiar | Trivy | GitHub Advanced Security |
|---|---|---|
| **Typ** | Narzędzie CLI (skaner) | Funkcje platformy (SaaS) |
| **Zakres** | Obrazy, IaC, K8s, zależności, sekrety, SBOM, licencje | Kod źródłowy (SAST), sekrety, zależności |
| **Analiza kodu aplikacji (SAST)** | ❌ (tylko zależności i konfiguracja) | ✅ CodeQL + AI detections |
| **Skanowanie obrazów kontenerów** | ✅ główna funkcja | ❌ natywnie (tylko przez import SARIF z innych narzędzi) |
| **IaC (Terraform, K8s YAML)** | ✅ bogaty zestaw reguł | ⚠️ ograniczone (AI detections, ewentualnie import SARIF) |
| **Klaster K8s (runtime config)** | ✅ `trivy k8s`, Trivy Operator | ❌ |
| **Sekrety** | ✅ wzorce (w plikach / obrazach) | ✅ wzorce + AI + push protection + historia Gita + unieważnianie u dostawców |
| **AI** | Zewnętrznie (MCP, k8sgpt) | Wbudowane (Autofix, generic secrets, AI detections) |
| **Naprawa** | Podaje wersję z poprawką (`Fixed Version`) | Generuje gotową zmianę w kodzie (Autofix), PR-y Dependabota |
| **Platforma** | Dowolna (GitHub, GitLab, Azure DevOps, Jenkins, lokalnie, offline) | Tylko GitHub |
| **Koszt** | 0 zł | 0 zł dla repo publicznych; płatne dla prywatnych |

**Wniosek:** narzędzia się **uzupełniają**. Typowy dojrzały setup to GHAS do kodu i sekretów oraz Trivy do obrazów, IaC i klastra, z wynikami Trivy wysyłanymi do zakładki *Security* w GitHubie.

---

## 4. Czy są bezpieczne?

### 4.1 Case study: atak na łańcuch dostaw Trivy (marzec 2026)

**Co się stało (CVE-2026-33634, GHSA-69fq-xp46-6x23):**

1. Na początku marca 2026 doszło do pierwszego incydentu z wyciekiem poświadczeń projektu. **Rotacja kluczy nie objęła wszystkich naraz** (nie była „atomowa”).
2. Grupa **TeamPCP** wykorzystała pozostały dostęp i 19–23 marca opublikowała złośliwe wersje:

| Komponent | Złośliwe wersje | Okno |
|---|---|---|
| Plik binarny `trivy` | **v0.69.4** | 19.03, ok. 3 h |
| `aquasecurity/trivy-action` | **76 z 77 tagów** podmienionych (wersje < 0.35.0) | 19–20.03 |
| `aquasecurity/setup-trivy` | wszystkie tagi v0.2.0–v0.2.6 | 19.03, ok. 4 h |
| Obrazy Docker Hub | **v0.69.5, v0.69.6** | 22–23.03, ok. 10 h |

3. Złośliwy kod **najpierw kradł sekrety**, a potem uruchamiał normalny skan, więc pipeline'y wyglądały na zdrowe. Kradzione były m.in.:
   - pamięć procesu runnera,
   - klucze SSH,
   - poświadczenia AWS, GCP i Azure,
   - tokeny Kubernetes,
   - konfiguracja Dockera.

   Dane były szyfrowane i wysyłane do atakujących albo do repozytoriów `tpcp-docs` tworzonych na koncie ofiary.

**Bezpieczne wersje (wg advisory):** binarka v0.69.2, v0.69.3 lub nowsze wydania po incydencie; `trivy-action` ≥ v0.35.0; `setup-trivy` v0.2.6 (ponownie opublikowana). **Sprawdź aktualne advisory.** Bezpieczna jest też wersja z `setup/README.md` (0.75.0).

**Lekcje z incydentu:**
- **Narzędzie bezpieczeństwa też jest elementem łańcucha dostaw**, i to szczególnie cennym celem, bo działa z dostępem do sekretów CI.
- **Przypinaj GitHub Actions do pełnego SHA**, nie do tagu (`@v0.35.0` da się podmienić, a commit SHA nie).
- **Weryfikuj podpisy** binarek i obrazów (cosign / sigstore).
- **Minimalne uprawnienia w CI:** `permissions:` w workflow, OIDC zamiast długożyjących kluczy, osobne sekrety per job.
- **Rotacja po incydencie musi być pełna i jednoczesna.**
- Jeśli używałeś Trivy w CI w dniach 19–23.03.2026: przejrzyj logi, **zrotuj wszystkie sekrety**, poszukaj repo `tpcp-docs` w organizacji.

> Ten incydent nie oznacza, że Trivy jest „niebezpieczny”. Projekt zareagował, opublikował pełne advisory i poprawki. Pokazuje jednak, że **każde** narzędzie trzeba wdrażać z zasadami bezpieczeństwa łańcucha dostaw. GHAS jest tu w innej sytuacji, bo działa jako usługa GitHuba, a nie kod uruchamiany w Twoim pipeline. Pamiętaj jednak, że akcje CodeQL też są GitHub Actions i również warto je przypinać do SHA.

### 4.2 Bezpieczeństwo danych i AI

| Aspekt | Trivy | GHAS |
|---|---|---|
| **Gdzie przetwarzane są dane** | Lokalnie. Trivy pobiera tylko bazy podatności (`ghcr.io/aquasecurity/trivy-db`, `trivy-java-db`), a Twój kod nigdzie nie jest wysyłany | Kod jest na GitHubie i tam analizowany |
| **AI** | Trivy MCP: wyniki skanu trafiają do **modelu używanego przez Twojego asystenta** (Claude, Copilot…), zgodnie z jego polityką danych | Autofix i AI detections: fragmenty kodu trafiają do modeli używanych przez GitHub (Microsoft/OpenAI/Anthropic). Dane **nie są używane do trenowania** (wg dokumentacji GitHub) |
| **Środowiska offline** | ✅ tryb air-gapped (lokalne lustro bazy, `--skip-db-update`, `--offline-scan`) | ❌ (GitHub Enterprise Server ma GHAS, ale funkcje AI wymagają połączenia z chmurą) |
| **Ryzyka AI** | Asystent może źle zinterpretować wynik lub zaproponować złą wersję pakietu | **Autofix może wygenerować niepoprawną lub niepełną poprawkę.** GitHub wprost zaleca review. AI wykrywanie sekretów ma więcej fałszywych alarmów niż wzorce |

### 4.3 Checklista wdrożenia

- [ ] Akcje CI przypięte do **pełnego SHA** (Trivy, CodeQL, upload-sarif); aktualizacje przez Dependabota.
- [ ] Weryfikacja podpisów binarek i obrazów (cosign).
- [ ] Minimalne `permissions:` w workflow (`contents: read`, `security-events: write` tylko tam, gdzie potrzeba).
- [ ] Brak długożyjących sekretów w CI: OIDC do chmury.
- [ ] Push protection włączona dla całej organizacji.
- [ ] Każda poprawka z Autofix przechodzi **code review i testy**.
- [ ] Polityka „blokujemy build tylko na CRITICAL/HIGH z dostępną poprawką”, żeby nie zabić zespołu szumem.
- [ ] Przy Trivy MCP: świadomość, że wyniki skanu (nazwy pakietów, ścieżki, czasem fragmenty konfiguracji) trafiają do LLM.

---

## 5. Jaką mają opinię?

### Trivy

**Plusy:**
- **De facto standard** skanowania obrazów w open source. Bardzo szybki, prosty (jeden plik binarny), szeroki zakres w jednym narzędziu.
- Dobra jakość baz podatności, niski próg wejścia, świetna integracja z CI i Kubernetesem.
- Darmowy, bez limitów, działa offline.

**Minusy:**
- **Marcowy incydent supply chain** mocno nadszarpnął zaufanie. W społeczności toczyła się dyskusja o przejściu na alternatywy (Grype, Docker Scout) albo o przypinaniu i weryfikacji wersji. Po incydencie Aqua wzmocniła procesy wydawnicze.
- Dużo alertów (szczególnie w dużych obrazach bazowych). Bez filtrów (`--ignore-unfixed`, `--severity`) wyniki bywają przytłaczające.
- Skanowanie IaC mniej dojrzałe niż wyspecjalizowane narzędzia (Checkov) w niektórych obszarach.
- Brak SAST dla kodu aplikacji.

### GitHub Advanced Security

**Plusy:**
- **Najlepsza integracja z workflow dewelopera**: wszystko dzieje się w PR, bez osobnego narzędzia.
- **Push protection** realnie zapobiega wyciekom (w przeciwieństwie do wykrywania po fakcie).
- **Copilot Autofix** dobrze oceniany: według danych GitHuba skraca czas naprawy wielokrotnie, a deweloperzy chętniej naprawiają, gdy dostają gotową poprawkę.
- CodeQL to jeden z najlepszych silników SAST, a dla open source wszystko jest za darmo.

**Minusy:**
- **Cena** dla repo prywatnych: 49 USD za aktywnego committera miesięcznie przy pełnym pakiecie. Dla dużych zespołów to znaczący koszt, a model „aktywnego committera” bywa trudny do przewidzenia.
- **Lock-in**: tylko GitHub. Firmy na GitLabie lub Azure DevOps mają inne rozwiązania (GitLab Ultimate, GHAS for Azure DevOps).
- CodeQL potrafi długo budować bazę dla dużych repozytoriów (minuty CI).
- Brak skanowania obrazów kontenerów i słabsze IaC, więc i tak potrzebne jest dodatkowe narzędzie.
- Poprawki Autofix bywają poprawne składniowo, ale nie w pełni rozwiązują problem. Review jest konieczne.

---

## 6. Licencje i koszty

### Trivy

| Element | Koszt |
|---|---|
| Trivy CLI, Trivy Operator, Trivy MCP, trivy-action | **0 zł** (Apache 2.0) |
| Aqua Platform (komercyjna) | wg oferty Aqua |
| Koszt AI przy Trivy MCP | wg asystenta, którego używasz (Claude Code, Copilot…) |

### GitHub Advanced Security

| Element | Repo publiczne | Repo prywatne (GitHub Team / Enterprise) |
|---|---|---|
| Secret scanning + push protection | **0 zł** | **Secret Protection: 19 USD / aktywny committer / mies.** |
| Copilot secret scanning (AI generic secrets) | — | w ramach Secret Protection (licencja Copilot niepotrzebna) |
| Code scanning (CodeQL) + Copilot Autofix | **0 zł** | **Code Security: 30 USD / aktywny committer / mies.** |
| Dependabot alerts i security updates | 0 zł | 0 zł |
| Dependency review | 0 zł | w ramach Code Security |
| Pełny GHAS | 0 zł | 49 USD / aktywny committer / mies. |
| Minuty GitHub Actions dla CodeQL | darmowe dla publicznych | wg planu Actions |

**„Aktywny committer”** to osoba, która w ostatnich 90 dniach zrobiła commit do repo z włączonym produktem. Płacisz tylko za repo, w których funkcja jest włączona.


---

## 7. Instalacja i użycie

### 7.1 Trivy: instalacja (bezpieczna)

```bash
# macOS / Linux (Homebrew)
brew install trivy

# Debian/Ubuntu (oficjalne repo APT)
sudo apt-get install -y wget gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install -y trivy

trivy --version   # upewnij się, że NIE jest to v0.69.4 / v0.69.5 / v0.69.6
```

Weryfikacja podpisu pobranej binarki (cosign, keyless):

```bash
cosign verify-blob trivy_<wersja>_Linux-64bit.tar.gz \
  --bundle trivy_<wersja>_Linux-64bit.tar.gz.sigstore.json \
  --certificate-identity-regexp 'https://github\.com/aquasecurity/trivy/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

> Dokładne nazwy plików podpisu sprawdź na stronie wydania i w advisory GHSA-69fq-xp46-6x23.

### 7.2 Trivy: podstawowe użycie

```bash
# Obraz kontenera: tylko istotne i naprawialne podatności
trivy image --severity HIGH,CRITICAL --ignore-unfixed nginx:1.27

# Projekt lokalny: zależności, sekrety, IaC
trivy fs --scanners vuln,secret,misconfig .

# IaC: Terraform / K8s YAML / Helm / Dockerfile
trivy config ./terraform
trivy config ./k8s-manifests

# Klaster Kubernetes (aktualny kontekst kubeconfig)
trivy k8s --report summary
trivy k8s --include-namespaces shop --report all

# Zgodność z benchmarkiem
trivy k8s --compliance k8s-cis-1.23 --report summary

# SBOM
trivy image --format cyclonedx --output sbom.json myapp:1.0
trivy sbom sbom.json

# Bramka w CI: kod wyjścia 1 przy CRITICAL
trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed myapp:1.0
```

Ignorowanie zaakceptowanych ryzyk (`.trivyignore`):

```
# CVE bez wpływu na nas: biblioteka nieużywana w runtime (decyzja: J. Kowalski, 2026-10-01, przegląd: 2027-01-01)
CVE-2025-12345
```

### 7.3 Trivy: GitHub Actions + wysyłka wyników do GHAS

```yaml
# .github/workflows/trivy.yml
name: trivy
on: [push, pull_request]

permissions:
  contents: read
  security-events: write   # wymagane do uploadu SARIF

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<PEŁNY_SHA>              # v5
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Trivy scan
        uses: aquasecurity/trivy-action@<PEŁNY_SHA>     # v0.35.0 lub nowszy, przypięty do SHA!
        with:
          image-ref: myapp:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: HIGH,CRITICAL
          ignore-unfixed: true

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@<PEŁNY_SHA>   # v3/v4
        with:
          sarif_file: trivy-results.sarif
```

SHA sprawdzisz poleceniem `git ls-remote https://github.com/aquasecurity/trivy-action refs/tags/v0.35.0` albo na stronie wydania. Dependabot (`package-ecosystem: github-actions`) sam będzie aktualizował SHA.

Wyniki pojawią się w *Security → Code scanning* jako alerty. Dla nich też działa Copilot Autofix (dla wspieranych typów alertów).

### 7.4 Trivy Operator (ciągłe skanowanie klastra)

```bash
helm repo add aqua https://aquasecurity.github.io/helm-charts/
helm repo update
helm install trivy-operator aqua/trivy-operator \
  -n trivy-system --create-namespace \
  --set trivy.ignoreUnfixed=true

kubectl get vulnerabilityreports -A -o wide
kubectl get configauditreports -A -o wide
```

### 7.5 Trivy + AI: MCP Server

```bash
# Instalacja pluginu MCP
trivy plugin install mcp

# Podłączenie do Claude Code
claude mcp add trivy -- trivy mcp
```

Przykładowe prompty w Claude Code:

```
Przeskanuj ten projekt Trivy pod kątem podatności HIGH i CRITICAL. Pogrupuj je według pakietu
i powiedz, które da się naprawić samą aktualizacją wersji.

Sprawdź konfigurację Terraform w katalogu ./infra i zaproponuj poprawki dla błędów konfiguracji.
Pokaż diff, ale niczego nie zmieniaj bez mojej zgody.

Przeskanuj obraz myapp:1.0 i wyjaśnij, które CVE są realnie groźne dla aplikacji webowej.
```

### 7.6 GitHub Advanced Security: włączenie

W repozytorium: **Settings → Advanced Security** (lub *Code security*):

1. **Dependency graph** i **Dependabot alerts** → *Enable*.
2. **Secret Protection**: *Secret scanning* → *Enable*, *Push protection* → *Enable*. Opcjonalnie *Copilot secret scanning* (generic secrets).
3. **Code scanning** → *CodeQL analysis* → **Default setup** (GitHub sam wykryje języki i skonfiguruje workflow) → *Enable CodeQL*.
4. **Copilot Autofix** włącza się domyślnie z code scanning (można wyłączyć na poziomie repo lub organizacji).

Dla całej organizacji: *Organization settings → Advanced Security → Configurations*. Tworzysz konfigurację bezpieczeństwa i przypisujesz ją do wszystkich repo.

Przez GitHub CLI (przykład dla jednego repo):

```bash
# Włączenie secret scanning i push protection
gh api -X PATCH repos/<org>/<repo> \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'

# Lista alertów code scanning
gh api repos/<org>/<repo>/code-scanning/alerts --jq '.[] | {number, rule: .rule.id, severity: .rule.security_severity_level, state}'
```

### 7.7 GHAS: jak wygląda praca z AI

**Copilot Autofix w PR:**
1. Deweloper otwiera PR z podatnym kodem (np. zapytanie SQL sklejane ze stringów).
2. CodeQL dodaje komentarz z alertem *SQL injection*.
3. Pod alertem pojawia się **„Copilot Autofix”**: wyjaśnienie podatności + proponowany diff (np. zapytanie parametryzowane).
4. Deweloper sprawdza, ewentualnie poprawia i klika *Commit suggestion*.

**Push protection:**

```bash
$ git push
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - GITHUB PUSH PROTECTION
remote:   Push cannot contain secrets
remote:   —— AWS Access Key ID ——————————————————————
remote:    locations:
remote:      - commit: 3f2a1b...  path: config/settings.py:12
```

Rozwiązanie: usuń sekret z historii (`git reset` / `git commit --amend` / `git rebase`), **zrotuj go**, przechowuj w secret managerze. Obejście („allow secret”) zostawia ślad audytowy.

**Security campaign:** *Security → Campaigns → Create campaign*. Wybierasz np. wszystkie alerty „XSS” w organizacji, Autofix generuje poprawki, a zespoły dostają zadania z terminem.

---

## Źródła

**Trivy**
- Repozytorium i dokumentacja: https://github.com/aquasecurity/trivy · https://trivy.dev
- Advisory ataku supply chain (CVE-2026-33634): https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23
- Aqua: Trivy supply chain attack — what you need to know: https://www.aquasec.com/blog/trivy-supply-chain-attack-what-you-need-to-know/
- Microsoft Security: wykrywanie i obrona przed kompromitacją Trivy: https://www.microsoft.com/en-us/security/blog/2026/03/24/detecting-investigating-defending-against-trivy-supply-chain-compromise/
- Wiz: Trivy compromised by TeamPCP: https://www.wiz.io/blog/trivy-compromised-teampcp-supply-chain-attack
- Trivy MCP Server: https://github.com/aquasecurity/trivy-mcp · https://www.aquasec.com/blog/security-that-speaks-your-language-trivy-mcp-server/
- Trivy Operator: https://github.com/aquasecurity/trivy-operator

**GitHub Advanced Security**
- Dokumentacja: https://docs.github.com/en/code-security
- AI w funkcjach bezpieczeństwa GitHub: https://docs.github.com/en/code-security/responsible-use/security-and-quality-ai-features
- Copilot secret scanning (generic secrets): https://docs.github.com/code-security/secret-scanning/about-the-detection-of-generic-secrets-with-secret-scanning
- AI security detections w PR (07.2026): https://github.blog/changelog/2026-07-14-code-scanning-shows-ai-security-detections-on-pull-requests/
- Secret scanning przez GitHub MCP Server (GA 05.2026): https://github.blog/changelog/2026-05-05-secret-scanning-with-github-mcp-server-is-now-generally-available/
- Cennik: https://github.com/pricing · https://github.com/security/advanced-security
