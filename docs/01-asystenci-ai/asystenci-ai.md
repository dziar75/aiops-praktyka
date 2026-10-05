# Asystenci AI do kodu — GitHub Copilot, Claude Code i OpenAI Codex

Materiał pomocniczy do Dnia 1, temat 2: *AI jako asystent w terminalu i edytorze: konfiguracja i pierwsze użycie*. Diagram architektury: [`architektura.html`](architektura.html).

> Stan na 2 października 2026. Cenniki, limity i nazwy modeli zmieniają się co kilka tygodni, więc w razie wątpliwości sprawdź linki w sekcji Źródła.

---

## TL;DR

| | **GitHub Copilot** | **Claude Code** | **OpenAI Codex** |
|---|---|---|---|
| **Jednym zdaniem** | Asystent wbudowany w IDE i GitHuba: od podpowiedzi w trakcie pisania po agenta, który z issue robi PR | Agent w terminalu, który dostaje zadanie i sam je wykonuje w repozytorium | Agent OpenAI działający lokalnie (CLI, IDE, aplikacja) i w chmurze (zadania kończone diffem lub PR) |
| **Autor** | GitHub (Microsoft) | Anthropic | OpenAI |
| **Główne miejsce pracy** | IDE + github.com (+ Copilot CLI) | Terminal (+ IDE, desktop, web) | Terminal / aplikacja + chmura ChatGPT |
| **Modele** | Do wyboru: OpenAI, Anthropic, Google | Tylko Claude | Tylko OpenAI |
| **Plik kontekstu projektu** | `.github/copilot-instructions.md`, `AGENTS.md` | `CLAUDE.md` (`AGENTS.md` tylko bez `CLAUDE.md` albo przez import `@AGENTS.md`) | `AGENTS.md` |
| **Licencja / koszt** | Własnościowy; Free, Pro 10 USD, Pro+ 39 USD, Max 100 USD, Business 19 USD, Enterprise 39 USD | Własnościowy; Pro 20 USD, Max od 100 USD, Team, Enterprise albo API | CLI open source (Apache 2.0); dostęp w planach ChatGPT (od Free) albo przez API |

**Najkrócej:** Copilot **pomaga człowiekowi pisać kod** i najlepiej zna GitHuba. Claude Code i Codex **wykonują zadanie za człowieka**: czytają repo, uruchamiają komendy i poprawiają wynik w pętli. Claude Code stawia na konfigurowalność (hooks, skills, subagenty), Codex na sandbox domyślnie i równoległe zadania w chmurze.

---

## 1. Podstawy: od podpowiedzi do agenta

Asystenci AI do kodu przeszli w trzy lata przez trzy etapy:

1. **Podpowiedzi (completions)**: model dopisuje kolejną linię lub funkcję w edytorze. Człowiek decyduje o wszystkim.
2. **Czat**: pytasz o kod, model odpowiada i proponuje zmiany, ale to Ty je wklejasz i uruchamiasz.
3. **Agent**: model dostaje zadanie i narzędzia (odczyt i zapis plików, terminal, MCP). Sam planuje, wykonuje komendy, czyta wyniki i iteruje, aż zadanie jest zrobione.

Dziś wszystkie trzy narzędzia mają tryb agenta. Różnią się tym, **skąd wyrosły** i **gdzie agent pracuje**:

| Gdzie pracuje agent | Copilot | Claude Code | Codex |
|---|---|---|---|
| **Lokalnie, w IDE** | Agent mode w VS Code / JetBrains / Visual Studio | Rozszerzenie VS Code / JetBrains | Rozszerzenie VS Code (i forków: Cursor, Windsurf) |
| **Lokalnie, w terminalu** | Copilot CLI | Claude Code CLI (rdzeń produktu) | Codex CLI |
| **W chmurze, asynchronicznie** | Coding agent: przypisujesz issue → PR | Sesje w claude.ai/code, Routines, GitHub Actions | Codex cloud: zadanie → diff / PR |

Dla DevOps najważniejszy jest **agent w terminalu**, bo ma dostęp do tych samych narzędzi co inżynier: `kubectl`, `terraform`, `aws`, `helm`, logi. To daje największą wartość i największe ryzyko (patrz rozdział 5).

---

## 2. Do czego służą?

### 2.1 GitHub Copilot

Asystent AI od GitHuba z najniższym progiem wejścia: instalujesz rozszerzenie i od razu dostajesz podpowiedzi.

Tryby pracy:

1. **Inline suggestions**: podpowiedzi w trakcie pisania (ghost text, *next edit suggestions*).
2. **Copilot Chat**: rozmowa o kodzie w IDE i na github.com: wyjaśnianie, refaktor, testy.
3. **Agent mode**: w IDE agent edytuje wiele plików, uruchamia komendy w terminalu i poprawia błędy. Korzysta z serwerów MCP.
4. **Coding agent (cloud agent)**: przypisujesz issue do Copilota, a on pracuje asynchronicznie w środowisku GitHub Actions i otwiera PR do review.
5. **Copilot CLI**: agent w terminalu (`copilot`), podobny w obsłudze do Claude Code.
6. **Code review**: automatyczna recenzja PR (temat Dnia 2).

Od planu Pro+ Copilot pozwala też **delegować zadania do agentów zewnętrznych**, m.in. Claude i Codex (preview). GitHub staje się więc „platformą dla agentów”, a nie tylko jednym agentem.

**Najlepsze dla:** zespołów, które żyją w GitHubie i chcą jednego, centralnie zarządzanego narzędzia (licencje, polityki, audyt).

### 2.2 Claude Code

Agent AI od Anthropic, zaprojektowany jako narzędzie terminalowe. Nie podpowiada linijek, tylko wykonuje zadania.

Jak działa:

1. **Pętla agenta**: model Claude planuje, czyta pliki, edytuje, uruchamia komendy (testy, `kubectl get`, `terraform plan`) i poprawia wynik.
2. **Uprawnienia**: tryby od „pytaj o każdą akcję”, przez *auto mode*, po *plan mode* (tylko analiza i plan, bez zmian). Reguły `allow` / `deny` w `settings.json`, sandbox dla Basha.
3. **Pamięć projektu**: `CLAUDE.md` w repo (konwencje, komendy, architektura), generowany przez `/init`. Do tego *auto memory*, którą agent prowadzi sam.
4. **Rozszerzenia**: serwery **MCP** (GitHub, Grafana, AWS, k8sgpt, Terraform), **skills** (pakiety instrukcji, np. `/deploy-staging`), **hooks** (skrypty przed i po akcjach agenta), **pluginy**.
5. **Subagenty i praca równoległa**: agent prowadzący rozdziela zadanie na kilka agentów.
6. **Automatyzacja**: tryb headless `claude -p`, GitHub Actions, GitLab CI, zadania cykliczne (*Routines*), **Agent SDK** do budowy własnych agentów.

Działa w terminalu, VS Code, JetBrains, aplikacji desktop, w przeglądarce (claude.ai/code) i w Slacku. Te same `CLAUDE.md`, ustawienia i serwery MCP działają we wszystkich tych miejscach.

**Najlepsze dla:** pracy operacyjnej i dużych zadań wieloplikowych, gdzie liczy się autonomia i możliwość dopasowania agenta do procesu zespołu.

### 2.3 OpenAI Codex

Agent od OpenAI w kilku postaciach połączonych jednym kontem ChatGPT.

Jak działa:

1. **Codex CLI**: open-source'owy agent w terminalu (Apache 2.0). Czyta repo, edytuje pliki i uruchamia komendy **w sandboksie systemowym**.
2. **Sandbox i zatwierdzanie**: tryby `read-only`, `workspace-write` (domyślny w repo Git: zapis tylko w katalogu roboczym, **sieć wyłączona**) i `danger-full-access`. Do tego polityka zatwierdzania (`on-request`, `never`).
3. **Codex cloud (ChatGPT Work)**: zadanie zlecone z przeglądarki, aplikacji lub GitHuba trafia do izolowanego kontenera z kopią repo. Agent pracuje w tle i oddaje diff lub PR. Można puścić wiele zadań równolegle.
4. **Kontekst**: `AGENTS.md` w repo (otwarty format, czytany też przez Copilota; Claude Code przez import `@AGENTS.md`). Konfiguracja w `~/.codex/config.toml`.
5. **Automatyzacja**: `codex exec` do skryptów i CI, serwery MCP, code review PR.

**Najlepsze dla:** zespołów w ekosystemie ChatGPT oraz zlecania wielu niezależnych zadań w tle.

---

## 3. Czym się różnią?

| Wymiar | GitHub Copilot | Claude Code | OpenAI Codex |
|---|---|---|---|
| **Filozofia** | Asystent w edytorze, który urósł do agenta | Agent od początku, terminal-first | Agent lokalny + agent w chmurze |
| **Podpowiedzi w trakcie pisania** | Tak (główna funkcja) | Nie | Nie |
| **Wybór modelu** | Wielu dostawców w jednej subskrypcji | Tylko Claude (Opus / Sonnet / Haiku) | Tylko modele OpenAI |
| **Model bezpieczeństwa wykonania** | Potwierdzanie komend, `--allow-tool` / `--deny-tool` w CLI, izolacja w Actions | Tryby uprawnień, `allow` / `deny` w `settings.json`, hooks, sandbox | Sandbox systemu operacyjnego **domyślnie**, sieć domyślnie wyłączona |
| **Konfiguracja projektu** | `copilot-instructions.md`, pliki instrukcji per ścieżka, `AGENTS.md` | `CLAUDE.md` (hierarchia: firma → użytkownik → projekt → katalog) | `AGENTS.md`, `config.toml` |
| **Rozszerzalność** | MCP, custom agents, skills w `.github/` | MCP, skills, hooks, subagenty, pluginy, Agent SDK | MCP, `config.toml` |
| **Praca w chmurze** | Coding agent (issue → PR) | Sesje web, Routines, `claude --cloud` | Codex cloud, wiele zadań równolegle |
| **CI/CD** | Coding agent, code review | `claude -p`, GitHub Actions, GitLab CI | `codex exec`, GitHub Action |
| **Integracja z GitHubem** | Natywna (najlepsza) | Przez GitHub App, Actions, MCP | Przez integrację ChatGPT z GitHubem |
| **Open source** | Nie | Nie | CLI tak |
| **Próg wejścia** | Najniższy | Średni (terminal, konfiguracja uprawnień) | Średni |

**Wspólny mianownik:** wszystkie trzy obsługują **MCP** i **pliki instrukcji w repo**. Dobrze napisany `AGENTS.md` / `CLAUDE.md` i te same serwery MCP przenoszą się między narzędziami. W praktyce wiele zespołów łączy Copilota w IDE z jednym agentem terminalowym.

---

## 4. Jaką mają opinię?

### GitHub Copilot

**Plusy:**
- Najszerzej wdrożony w firmach. Często jest już kupiony, więc nie trzeba przechodzić nowego procesu zakupowego i oceny bezpieczeństwa.
- Wybór modeli w jednej subskrypcji: można porównać Claude i GPT bez osobnych kont.
- Coding agent i code review dobrze wpisują się w istniejący proces PR.

**Minusy:**
- Agent mode i CLI długo goniły konkurencję. Wiele osób ocenia, że ten sam model działa lepiej w „natywnym” narzędziu (Claude w Claude Code, GPT w Codex).
- Rozliczanie w **AI credits** (od 2026) jest mniej przewidywalne niż stała opłata. Po zakończeniu promocji 31.08.2026 pula kredytów w planach firmowych spadła.

### Claude Code

**Plusy:**
- Uznawany za punkt odniesienia dla agentów terminalowych. Wiele funkcji (hooks, skills, subagenty) inne narzędzia później skopiowały.
- Bardzo dobre radzenie sobie z dużymi zadaniami, refaktorem i pracą operacyjną.
- Dużo kontroli: można precyzyjnie ustawić, co agent może, a czego nie.

**Minusy:**
- Tylko modele Claude.
- Przy intensywnym użyciu limity planu Pro szybko się kończą; do pracy na co dzień ludzie przechodzą na Max albo API.
- Na początku wymaga dyscypliny: bez przemyślanych uprawnień łatwo dać agentowi za dużo swobody.

### OpenAI Codex

**Plusy:**
- Najmocniejszy sandbox „z pudełka”: domyślnie brak sieci i zapis tylko w katalogu roboczym.
- Wygodne zlecanie wielu zadań w chmurze i odbieranie gotowych PR.
- Otwarty kod CLI, dostęp już w darmowym planie ChatGPT.

**Minusy:**
- Tylko modele OpenAI. Limity w planach Plus/Business liczone w oknach 5-godzinnych i mocno zależne od wybranego modelu.
- Ekosystem rozszerzeń mniejszy niż w Claude Code.
- Częste zmiany nazw produktów i modeli utrudniają śledzenie dokumentacji (stare tutoriale opisują inny produkt o tej samej nazwie).

**Ogólny werdykt:** nie ma jednego zwycięzcy. Copilot wygrywa integracją i łatwością wdrożenia w firmie, Claude Code autonomią i konfigurowalnością, Codex bezpiecznymi domyślnymi ustawieniami i pracą w chmurze.

---

## 5. Czy są bezpieczne?

Krótka odpowiedź: **same narzędzia są dojrzałe, ale agent ma takie uprawnienia jak Ty.** Jeśli w terminalu masz kubeconfig z rolą cluster-admin i profil AWS z prawem do `terraform apply`, to agent też je ma.

### Wspólne ryzyka

| Ryzyko | Opis | Mitygacja |
|---|---|---|
| **Wyciek danych do dostawcy LLM** | Kod, logi, wyniki `kubectl describe`, pliki `.env` i `*.tfstate` trafiają do modelu jako kontekst | Reguły blokujące odczyt plików z sekretami, plany firmowe bez trenowania na danych, DPA |
| **Zbyt szerokie uprawnienia** | Agent wykonuje komendy z Twoimi poświadczeniami | Osobny kubeconfig read-only, rola IAM read-only, `deny` dla `kubectl delete`, `terraform apply` |
| **Prompt injection** | Złośliwa treść w README, issue, logach czy odpowiedzi MCP steruje agentem | Tryb z potwierdzaniem komend, ograniczony dostęp do sieci, zaufane serwery MCP |
| **Halucynacje** | Agent wymyśla flagę, atrybut Terraform albo „naprawia” nie ten zasób | Review każdej zmiany, `plan` / `--dry-run=server` przed wykonaniem |
| **Niezaufane serwery MCP i pluginy** | Serwer MCP to kod z pełnym dostępem do tego, co mu dasz | Tylko sprawdzone źródła, przypięte wersje, minimalne tokeny |

### Specyfika narzędzi

- **Copilot:** coding agent pracuje w izolowanym środowisku Actions z ograniczonym dostępem do sieci (firewall z listą dozwolonych domen). Administrator organizacji może wyłączać modele, funkcje i wykluczać pliki z kontekstu. Copilot CLI ma `--allow-tool` / `--deny-tool` oraz niebezpieczny tryb `/yolo`.
- **Claude Code:** reguły `permissions.allow` / `permissions.deny` w `settings.json` (też na poziomie firmy, nienadpisywalne przez użytkownika), sandbox dla poleceń Bash, hooks blokujące wybrane komendy, *plan mode* do bezpiecznej analizy. Flaga `--dangerously-skip-permissions` wyłącza pytania i powinna być używana tylko w izolowanym kontenerze.
- **Codex:** sandbox systemu operacyjnego jest włączony domyślnie, a sieć wyłączona. Tryb `danger-full-access` (alias `--yolo`) wyłącza sandbox i zatwierdzanie. Dostęp do sieci włącza się świadomie w `config.toml`, z listą dozwolonych domen.

### MCP czy CLI?

Częste pytanie z sali: „po co serwer MCP do Kubernetesa, skoro agent ma `kubectl`?”. Krótka odpowiedź: w terminalu często nie trzeba.

| | Agent + CLI (`kubectl`, `gh`, `aws`) | Agent + serwer MCP |
|---|---|---|
| **Znajomość narzędzia** | Model zna `kubectl` z ogromnej liczby przykładów | Model poznaje narzędzia z opisu przekazanego w sesji |
| **Koszt kontekstu** | Wynik przycinasz przed wysłaniem (`-o jsonpath`, `jq`, `--tail`) | Opisy wszystkich narzędzi idą w każdym zapytaniu; wynik narzędzia trafia w całości |
| **Składanie operacji** | Potoki: `get … \| jq \| sort` w jednym kroku | Kilka wywołań, wyniki łączy model |
| **Gdzie działa** | Tylko tam, gdzie agent ma powłokę | Także czat w przeglądarce, IDE, aplikacja desktop |
| **Kontrola uprawnień w agencie** | Wzorce na Basha, które da się obejść | `allow` / `deny` na nazwę narzędzia, bez obejść wzorcem |
| **Praca zespołowa** | Każdy ma kubeconfig na laptopie | Serwer w klastrze: jeden SA, jeden endpoint, jeden audyt |
| **Zależności** | Narzędzia, które i tak masz | Dodatkowy proces (np. z npm) do przypięcia i zaufania |

Co wyszło w testach przed szkoleniem (3.10): reguły `deny` na Basha przeciekały. `python3 -c "open('.env')"` ominął blokadę odczytu `.env`, `kubectl get SECRET` przeszedł przez `Bash(*secret*)` (wzorce rozróżniają wielkość liter, kubectl nie), a agent sklejał komendy (`P=…; kubectl …`). `deny` na `mcp__k8s__pods_delete` takich dziur nie ma. Z drugiej strony serwer MCP Kubernetes w domyślnej konfiguracji miał narzędzie `configuration_view`, które oddało modelowi kubeconfig z tokenem, więc MCP też trzeba skonfigurować świadomie.

**Kiedy co:**
- **CLI:** agent w terminalu, klaster, do którego i tak masz dostęp, osobny kubeconfig tylko do odczytu.
- **MCP:** brak terminala; potrzeba twardej blokady konkretnych operacji; wspólna brama dla zespołu (serwer w klastrze z własnym ServiceAccountem, uwierzytelnianiem i TLS); system bez dobrego CLI.

**Wspólny mianownik:** ani CLI, ani MCP nie jest granicą bezpieczeństwa. Granicą jest tożsamość, z którą agent dochodzi do systemu: `kubectl` z kubeconfigiem tylko do odczytu jest tak samo bezpieczny jak MCP z tym samym tokenem.

**Gdzie działa serwer MCP z dema:** lokalnie, jako proces potomny Claude Code (transport stdio, bez portu), na czas sesji. Na klastrze są tylko ServiceAccount, Role i RoleBinding. Wersja „w klastrze” to ten sam serwer jako Deployment z `--port` (transport HTTP) i SA poda — wtedy trzeba zabezpieczyć endpoint.

### Checklista przed wpuszczeniem agenta na środowisko

- [ ] Czy polityka firmy pozwala wysyłać kod i logi do danego dostawcy? Jaki plan (firmowy, bez trenowania na danych)?
- [ ] Reguły blokujące odczyt `.env`, `*.tfstate`, `~/.aws/credentials`, kubeconfigów?
- [ ] Osobne, read-only poświadczenia do klastra i chmury?
- [ ] Komendy niszczące (`delete`, `apply`, `destroy`) na liście `deny` albo wymagają potwierdzenia?
- [ ] Lista zaufanych serwerów MCP z przypiętymi wersjami?
- [ ] Brak trybów „yolo” poza jednorazowym kontenerem?
- [ ] Limity kosztów (budżet API, limity kredytów)?

---

## 6. Licencje i koszty

| Element | Licencja | Koszt |
|---|---|---|
| **GitHub Copilot Free** | Własnościowa | 0 USD: 2000 podpowiedzi/mies., ograniczony czat i agent, bez code review |
| **Copilot Pro / Pro+ / Max** | Własnościowa | 10 / 39 / 100 USD miesięcznie (indywidualnie), z pulą AI credits |
| **Copilot Business / Enterprise** | Własnościowa | 19 / 39 USD na użytkownika miesięcznie; kredyty wspólne dla firmy, nadwyżka 0,01 USD za kredyt |
| **Claude Pro** | Własnościowa | 20 USD miesięcznie (17 USD przy płatności rocznej), zawiera Claude Code |
| **Claude Max** | Własnościowa | od 100 USD miesięcznie (5× lub 20× więcej użycia niż Pro) |
| **Claude Team / Enterprise** | Własnościowa | Team: 20 USD (Standard) lub 100 USD (Premium) za stanowisko; Enterprise: 20 USD + rozliczenie za użycie |
| **Claude Code przez API** | Własnościowa | Płatność za tokeny (Anthropic API, AWS Bedrock, Google Vertex AI) |
| **Codex CLI** | Apache 2.0 | 0 USD za samo narzędzie |
| **Codex w ChatGPT** | Własnościowa | Free, Go 8 USD, Plus 20 USD, Pro 100–500 USD, Business 20 USD za użytkownika, Enterprise wycena indywidualna; albo klucz API |


---

## 7. Instalacja i użycie

### 7.1 Claude Code

```bash
# macOS / Linux / WSL (instalator natywny, aktualizuje się sam)
curl -fsSL https://claude.ai/install.sh | bash

# albo Homebrew (bez automatycznych aktualizacji)
brew install --cask claude-code

claude --version
cd moje-repo && claude
```

Pierwsze kroki (zgodnie z LAB-em rozgrzewkowym):

```text
/help          # lista komend
/status        # konto, model, ustawienia
/model         # zmiana modelu
/init          # wygenerowanie CLAUDE.md na podstawie repo
shift+tab      # przełączanie trybów: normalny → auto-accept → plan mode
```

Blokada odczytu plików z sekretami w `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(**/*.tfstate)",
      "Bash(kubectl delete:*)",
      "Bash(terraform apply:*)"
    ]
  }
}
```

Podłączenie serwera MCP i tryb headless:

```bash
# Serwer MCP (przykład: k8sgpt jako narzędzie dla agenta)
claude mcp add k8sgpt -- k8sgpt serve --mcp

# Jednorazowe zadanie bez interakcji (skrypty, CI)
kubectl get events -n shop --sort-by=.lastTimestamp | tail -50 \
  | claude -p "Wyjaśnij, co się dzieje w namespace shop. Nie wykonuj żadnych komend."
```

### 7.2 GitHub Copilot CLI

```bash
# macOS / Linux
brew install --cask copilot-cli
# lub: npm install -g @github/copilot

cd moje-repo && copilot
# przy pierwszym uruchomieniu: /login
```

Kontrola uprawnień i tryb nieinteraktywny:

```bash
# Pozwól tylko na odczyt przez kubectl, zablokuj usuwanie
copilot -p "Sprawdź, dlaczego pody w namespace shop się restartują" \
  --allow-tool 'shell(kubectl get)' \
  --allow-tool 'shell(kubectl describe)' \
  --deny-tool 'shell(kubectl delete)'
```

Instrukcje projektu: `.github/copilot-instructions.md` (Copilot czyta też `AGENTS.md`). Serwery MCP: `copilot mcp` w CLI albo `.vscode/mcp.json` w VS Code.

### 7.3 OpenAI Codex CLI

```bash
# macOS / Linux
curl -fsSL https://chatgpt.com/codex/install.sh | sh
# lub: brew install --cask codex
# lub: npm install -g @openai/codex

cd moje-repo && codex
# logowanie kontem ChatGPT albo kluczem API
```

Tryby sandboksa i zatwierdzania:

```bash
# Tylko odczyt: bezpieczne wyjaśnianie repo
codex --sandbox read-only --ask-for-approval on-request

# Zapis w katalogu roboczym, bez sieci (domyślne w repo Git)
codex --sandbox workspace-write --ask-for-approval on-request

# Nieinteraktywnie, np. w CI
codex exec --sandbox workspace-write "Dodaj testy do skryptu backup.sh"
```

Włączenie sieci (świadomie, tylko gdy potrzebne) w `~/.codex/config.toml`:

```toml
[sandbox_workspace_write]
network_access = true
```

### 7.4 Jeden plik instrukcji dla wszystkich narzędzi

Żeby nie utrzymywać trzech plików, trzymaj wspólne zasady w `AGENTS.md`, a w `CLAUDE.md` tylko import. Bez importu Claude Code przy istniejącym `CLAUDE.md` w ogóle nie czyta `AGENTS.md`:

```markdown
<!-- CLAUDE.md -->
@AGENTS.md

## Specyficzne dla Claude Code
- Przed zmianą w Terraform uruchom `terraform validate` i `tflint`.
```

---

## Źródła

**GitHub Copilot**
- Plany i cennik: https://github.com/features/copilot/plans
- Instalacja Copilot CLI: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli
- Copilot CLI, opis komend: https://docs.github.com/en/copilot/reference/cli-command-reference
- Instrukcje repozytorium: https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot
- Ceny Business/Enterprise i AI credits (źródło wtórne): https://agentmarketplace.ai/github-copilot-enterprise-pricing

**Claude Code**
- Przegląd i instalacja: https://code.claude.com/docs/en/overview
- Ustawienia i uprawnienia: https://code.claude.com/docs/en/settings
- Pamięć i `CLAUDE.md`: https://code.claude.com/docs/en/memory
- Cennik planów: https://claude.com/pricing

**OpenAI Codex**
- Repozytorium CLI: https://github.com/openai/codex
- Plany i limity: https://learn.chatgpt.com/docs/pricing
- Sandbox i zatwierdzanie: https://learn.chatgpt.com/docs/agent-approvals-security
