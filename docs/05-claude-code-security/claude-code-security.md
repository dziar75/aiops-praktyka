# Claude Code — bezpieczeństwo i uprawnienia agenta

Diagram architektury: [`architektura.html`](architektura.html). Porównanie wszystkich warstw, które ograniczają agenta: od `CLAUDE.md`, przez tryby uprawnień i `settings.json` (allow/ask/deny), hooki i sandbox, po kontener i dedykowany runner.
- **Dzień 1, temat 2:** główne miejsce, przy demie z regułami `deny` i sandboksem.
- **Dzień 3, temat 3:** krótki powrót, hooki i izolacja jako bariery dla agenta działającego bez człowieka.

> Stan na 4.10.2026. Zachowanie deny i sandboksa sprawdzone 3.10 na Claude Code 2.1.288. Tryby, kolejność hooków wobec reguł i klucze managed settings: według dokumentacji ([Permission modes](https://code.claude.com/docs/en/permission-modes), [Permissions](https://code.claude.com/docs/en/permissions), [Hooks](https://code.claude.com/docs/en/hooks), [Sandboxing](https://code.claude.com/docs/en/sandboxing), [Devcontainer](https://code.claude.com/docs/en/devcontainer)). Skrypty hooków z przykładów to szkice: przetestuj je, zanim użyjesz ich w zespole.

---

## Model warstw ochrony

Warstwy się nie wykluczają, tylko składają. Każda niższa łapie to, co przepuściła wyższa: deny nie rozpozna skryptu w Pythonie, ale sandbox go zatrzyma; sandbox nie obejmuje MCP, ale rola IAM już tak.

| Kto egzekwuje | Warstwa | Co robi |
|---|---|---|
| model | `CLAUDE.md` / `AGENTS.md` | prośba w kontekście; jedno zdanie nacisku wystarcza, by ją obejść |
| człowiek | tryb uprawnień | ustala, kiedy pytać; granica jest tak dobra jak uwaga osoby, która klika |
| — | — | **nad kreską: prosi albo pyta · pod kreską: blokuje niezależnie od modelu** |
| Claude Code | `settings.json`: allow / ask / deny | stałe reguły na narzędzia i ścieżki; skrypty w Bashu potrafią je ominąć |
| Twój skrypt | hook `PreToolUse` | ocenia każde wywołanie przed wykonaniem: warunki, wyjątki, log audytu |
| system operacyjny | sandbox | Bash i procesy potomne nie wyjdą poza dozwolone pliki i domeny |
| infrastruktura | kontener / dedykowany runner + rola IAM | agent może wszystko, ale w jego zasięgu nie ma nic cennego |

---

## Tryby uprawnień

Tryb ustala punkt wyjścia: co rusza bez pytania. Reguły z `settings.json` kładziesz na wierzch, a **deny blokuje w każdym trybie, także w `bypassPermissions`**. Przełączasz `Shift+Tab` w sesji, flagą `--permission-mode` albo na stałe przez `"defaultMode"` w `settings.json`.

| Tryb | Co idzie bez pytania | Do czego |
|---|---|---|
| `default` (w CLI: Manual) | tylko odczyty | wrażliwa praca, nieznane repo |
| `acceptEdits` | odczyty, edycje plików, proste komendy plikowe (`mkdir`, `mv`, `cp`) | iteracja nad kodem, który i tak przeglądasz |
| `plan` | odczyty; agent planuje, niczego nie zmienia | analiza przed zmianą |
| `auto` | wszystko, ale każdą akcję ocenia drugi model (klasyfikator) | długie zadania bez zmęczenia klikaniem |
| `dontAsk` | odczyty i to, co jest w `allow`; reszta **automatycznie odrzucona** | CI i skrypty z dokładną listą dozwolonych narzędzi |
| `bypassPermissions` | wszystko, bez sprawdzeń | tylko izolowany kontener lub VM |

**Uwaga na wersję:** od Claude Code 2.1.283 sesja interaktywna startuje domyślnie w trybie `auto`. W `auto` część pytań o zgodę po prostu się nie pojawi — na czas dema ustaw `default`.

**Pułapka:** komendy tylko do odczytu (`ls`, `cat`, `grep`, `head`) idą bez pytania w każdym trybie. Tryb nie ochroni `.env` przed `cat`, robi to dopiero reguła deny.

**Przykład CI:**

```bash
claude -p "uruchom testy i opisz błędy" \
  --permission-mode dontAsk \
  --allowedTools "Bash(npm test)" "Read"
```

Agent może tylko czytać i uruchomić `npm test`. Każda inna próba kończy się odmową, a nie zawieszeniem joba na pytaniu.

**Dla firmy (managed settings):** `disableBypassPermissionsMode` wyłącza tryb bez sprawdzeń, `permissions.disableAutoMode: "disable"` usuwa `auto` z menu.

---

## settings.json: allow, ask, deny

Reguły w `permissions` decydują, czy narzędzie ruszy bez pytania, z pytaniem, czy wcale. Sprawdza je Claude Code, nie model, więc „zgadzam się” w czacie ich nie zmienia. Kolejność ważności: **deny > ask > allow**.

| Lista | Skutek | Typowe użycie |
|---|---|---|
| `allow` | narzędzie rusza bez pytania | `npm test`, `kubectl get`, `git status` |
| `ask` | zawsze pytanie o zgodę, nawet gdy coś w `allow` pasuje | `git push`, `kubectl apply`, `terraform apply` |
| `deny` | blokada, żadna zgoda jej nie zdejmie | `.env`, `*.tfstate`, `~/.aws/**`, `rm -rf` |
| (brak reguły) | zależy od trybu: odczyt w repo idzie sam, edycja i Bash pytają | — |

### Gdzie leży plik i kto wygrywa

| Plik | Zasięg | W gicie? |
|---|---|---|
| managed settings (macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`, Linux: `/etc/claude-code/managed-settings.json`) | cała firma, użytkownik nie nadpisze | nie, wdraża IT/MDM |
| `.claude/settings.local.json` | ja w tym repo | nie |
| `.claude/settings.json` | cały zespół w tym repo | tak |
| `~/.claude/settings.json` | ja we wszystkich repo | nie |

Reguły z różnych plików się sumują. Deny z dowolnego poziomu wygrywa z allow z każdego innego. Reguły `allow` z `.claude/settings.json` działają dopiero po zaakceptowaniu okna zaufania folderu (trust dialog); `deny` i `ask` od razu. Zmiany działają od **nowej sesji**.

### Składnia reguł — ściąga

| Reguła | Co znaczy |
|---|---|
| `Read(.env)` | każdy `.env` w projekcie i głębiej (= `Read(**/.env)`) |
| `Read(./.env)` | tylko `.env` w katalogu bieżącym |
| `Read(//etc/**)` / `Read(~/.aws/**)` | ścieżka od korzenia / od katalogu domowego |
| `Edit(src/**)` | edycja tylko pod `src/` |
| `Bash(git log *)` | `git log` z dowolnymi argumentami; spacja przed `*` ma znaczenie (`Bash(ls *)` nie złapie `lsof`) |
| `WebFetch(domain:docs.k8s.io)` | pobieranie tylko z tej domeny |
| `mcp__kubernetes` / `mcp__kubernetes__pods_list` | cały serwer MCP / jedno jego narzędzie |

### Przykład: repo zespołu infrastruktury

```json
{
  "permissions": {
    "allow": [
      "Bash(kubectl get *)",
      "Bash(kubectl describe *)",
      "Bash(terraform plan *)",
      "Bash(git status)",
      "Bash(git diff *)"
    ],
    "ask": [
      "Bash(kubectl apply *)",
      "Bash(terraform apply *)",
      "Bash(git push *)"
    ],
    "deny": [
      "Read(.env)",
      "Read(**/*.tfstate)",
      "Read(~/.aws/**)",
      "Bash(kubectl delete *)"
    ]
  }
}
```

### Czego deny nie widzi (sprawdzone 3.10, Claude Code 2.1.288)

| Próba odczytu `.env` | `Read(.env)` w deny |
|---|---|
| narzędzie Read, Grep, Glob, `@.env` | zablokowane |
| `cat .env`, `head`, `tail`, `sed`, `< .env` | zablokowane (Claude Code rozpoznaje te komendy) |
| `python3 -c "open('.env')"`, `node`, `/usr/bin/grep` | **nie rozpozna**, zostaje pytanie o zgodę |
| `grep -r HASŁO .` (bez nazwy pliku) | **nie rozpozna** |

Wniosek: deny na argumenty Basha (`Bash(cat .env*)`) łatwo obejść przez `bash -c` czy pełną ścieżkę. Pliki chroni `Read(...)` + sandbox, a komendy spoza wąskiej listy `allow` zostają na pytaniu.

---

## Hooki

Hook to Twój skrypt, który Claude Code uruchamia przy określonym zdarzeniu. Dostaje JSON na stdin (jakie narzędzie, z jakimi argumentami) i odpowiada kodem wyjścia albo JSON-em. Reguła w `settings.json` mówi „ten wzorzec tak/nie”, hook może sprawdzić **dowolny warunek**.

### Zdarzenia, które mają znaczenie dla bezpieczeństwa

| Zdarzenie | Kiedy | Do czego |
|---|---|---|
| `PreToolUse` | przed wywołaniem narzędzia | blokada, wymuszenie pytania, zgoda bez pytania |
| `PostToolUse` | po wywołaniu | log audytu, formatowanie, skan wyniku |
| `UserPromptSubmit` | po wysłaniu promptu | wykrycie sekretu wklejonego do czatu |
| `PermissionRequest` | gdy ma się pojawić pytanie o zgodę | własna polityka zamiast klikania |
| `SessionStart` | na starcie sesji | sprawdzenie środowiska, np. czy `kubectl` wskazuje właściwy kontekst |

Rodzaje hooków: `command` (skrypt), `http` (POST do serwisu), `prompt` i `agent` (ocena przez model), `mcp_tool`. Do bezpieczeństwa wybieraj `command` albo `http`: są deterministyczne i dają się przetestować.

### Jak hook odpowiada

| Odpowiedź | Skutek |
|---|---|
| `exit 0`, nic na stdout | brak decyzji, działają zwykłe reguły |
| `exit 2` + powód na stderr | blokada; powód trafia do modelu, więc agent wie, czemu odmówiono |
| inny kod wyjścia | błąd hooka, wywołanie idzie dalej (hook nie domyka się sam!) |
| JSON `permissionDecision`: `deny` / `ask` / `allow` | odpowiednio: blokada, wymuszone pytanie, zgoda bez pytania |

**Kolejność wobec reguł:** blokada z hooka (`exit 2`) wygrywa z `allow`, także w `bypassPermissions`. Odwrotnie nie: `allow` z hooka **nie** zdejmuje reguły `deny` ani `ask` z `settings.json`.

### Konfiguracja w `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/kubectl-tylko-demo.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "jq -c '{tool: .tool_name, input: .tool_input}' >> ~/.claude/audit.jsonl" }
        ]
      }
    ]
  }
}
```

`matcher` to nazwa narzędzia albo regex: `Bash`, `Edit|Write`, `mcp__kubernetes__.*`.

### Przykład 1: `kubectl` poza namespace `demo` wymaga zgody

```bash
#!/usr/bin/env bash
# .claude/hooks/kubectl-tylko-demo.sh
cmd=$(jq -r '.tool_input.command // empty')

if [[ $cmd == kubectl* ]] && [[ $cmd != *"-n demo"* ]]; then
  jq -n '{hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: "kubectl poza namespace demo"
  }}'
fi
exit 0
```

Tego nie zapiszesz regułą w `settings.json`. `Bash(kubectl * -n demo *)` nie złapie `--namespace=demo` ani flagi na końcu komendy, a reguły nie mają „nie zawiera”.

### Przykład 2: twarda blokada `terraform apply` i `kubectl delete`

```bash
#!/usr/bin/env bash
cmd=$(jq -r '.tool_input.command // empty')

if echo "$cmd" | grep -Eq 'terraform +(apply|destroy)|kubectl +delete'; then
  echo "Zmiany w infrastrukturze tylko przez pipeline, nie z agenta" >&2
  exit 2
fi
exit 0
```

Agent dostaje komunikat ze stderr i zwykle proponuje alternatywę, np. przygotowanie PR.

### Przykład 3: log audytu

Hook `PostToolUse` z konfiguracji powyżej dopisuje każde wywołanie do `~/.claude/audit.jsonl`. Po sesji masz pełną listę: co agent czytał i co uruchomił.

**Granice hooków:** hook na Bashu sprawdza tekst komendy, więc `python3 -c "open('.e'+'nv')"` przejdzie przez filtr na `.env`. Hook dobrze pilnuje polityki (co wolno robić), a sandbox granic (do czego w ogóle jest dostęp). Hook działa z Twoimi uprawnieniami, więc traktuj go jak kod produkcyjny: przegląd, testy, w firmie przez managed settings z `allowManagedHooksOnly`.

---

## settings.json czy hook?

Krótko: **`settings.json` to lista „tak/nie/pytaj” dla wzorców, hook to program, który podejmuje decyzję.** Zaczynaj od reguł, hook dokładaj tam, gdzie reguła nie umie wyrazić warunku.

| Cecha | `permissions` w `settings.json` | Hook `PreToolUse` |
|---|---|---|
| Forma | lista wzorców (`Bash(git push *)`) | skrypt, usługa HTTP albo model |
| Logika | pasuje / nie pasuje | dowolna: warunki, wyjątki, kontekst, zewnętrzne API |
| Wynik | allow, ask, deny | allow, ask, deny + powód dla modelu |
| Pliki | `Read(...)` łapie Read, Grep, `cat`, `head` | tylko to, co sam wyczytasz z argumentów |
| Co może zepsuć | nic, najwyżej zablokuje za dużo | błąd w skrypcie = przepuszczone wywołanie, wolniejsze akcje |
| Wobec drugiego | deny z reguły wygrywa z `allow` z hooka | blokada z hooka wygrywa z `allow` z reguły |
| Audyt | brak | tak (`PostToolUse`, log, wysyłka do SIEM) |
| Koszt | minuty, czytelne dla każdego | godziny, wymaga testów i przeglądu |

### Ten sam problem na dwa sposoby: „nie usuwaj zasobów w klastrze”

**Reguła** — prosto, ale tylko po tekście komendy:

```json
{ "permissions": { "deny": ["Bash(kubectl delete *)"] } }
```

Złapie `kubectl delete pod x`. Nie złapie `kubectl -n demo delete pod x` (flaga przed czasownikiem), `bash -c "kubectl delete …"` ani `kubectl apply --prune`.

**Hook** — rozumie komendę po swojemu i może mieć wyjątek:

```bash
cmd=$(jq -r '.tool_input.command // empty')
if echo "$cmd" | grep -Eq 'kubectl\b.*\b(delete|drain|--prune)\b'; then
  if [[ $cmd == *"-n sandbox"* ]]; then exit 0; fi   # w sandbox wolno
  echo "Usuwanie zasobów tylko w namespace sandbox" >&2
  exit 2
fi
```

**Rola w klastrze (RBAC)** — najpewniej: ServiceAccount agenta nie ma czasownika `delete` w RBAC. Wtedy nieważne, jak sformułuje komendę.

### Kiedy co

| Sytuacja | Wybierz |
|---|---|
| stały zakaz pliku lub katalogu | `Read(...)` / `Edit(...)` w deny + sandbox |
| stała lista bezpiecznych komend | `allow` |
| „zawsze pytaj przed” | `ask` |
| warunek (namespace, gałąź, godzina, środowisko) | hook |
| potrzebny log lub raport | hook `PostToolUse` |
| polityka dla całej firmy | managed settings (reguły + hooki) |

---

## Sandbox Claude Code

Sandbox domyka to, czego deny nie rozpoznaje: blokuje dostęp na poziomie systemu operacyjnego, więc `python3`, `node` i `/usr/bin/grep` też dostają `Operation not permitted`. Działa na macOS (Seatbelt), Linuksie i WSL2 (bubblewrap). Włączasz go przez `/sandbox` w sesji albo w `settings.json`.

```json
{
  "permissions": {
    "deny": ["Read(.env)", "Read(**/*.tfstate)"]
  },
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "filesystem": {
      "denyRead": ["./.env", "./infra/terraform.tfstate"]
    }
  }
}
```

| Ustawienie | Co robi |
|---|---|
| `enabled: true` | Bash i jego procesy potomne działają w sandboksie |
| `filesystem.denyRead` | zakaz odczytu dla każdego procesu z Basha; ścieżki z `Read(...)` deny też tu trafiają |
| `allowUnsandboxedCommands: false` | agent nie może poprosić o ponowienie komendy poza sandboksem |
| `autoAllowBashIfSandboxed` (domyślnie włączone) | komendy w sandboksie idą bez pytania; granicę wyznacza system, nie Twoje kliknięcie |

**Sieć:** `sandbox.network.allowedDomains` ogranicza, dokąd Bash może się połączyć, np. tylko `registry.npmjs.org` i `github.com`. To chroni przed wysłaniem sekretu przez `curl` na obcy serwer.

**Czego sandbox nie obejmuje:** narzędzi Read i Edit (te pilnują reguły `permissions`), serwerów MCP i hooków. Sandbox i deny to więc para, nie zamienniki.

**Pułapka z testu:** przy `Read(.env.*)` + wyjątku `Read(!.env.example)` sandbox zablokował też `.env.example`, bo wyjątek nie przeszedł do sandboksa. W sandboksie podawaj dokładne ścieżki.

---

## Izolacja zewnętrzna: kontener i dedykowany runner

Wszystko powyżej działa **wewnątrz** Claude Code. Izolacja zewnętrzna zakłada, że agent może zrobić wszystko, i ogranicza to, co w ogóle jest w jego zasięgu: pliki, sieć, poświadczenia. To jedyne miejsce, gdzie `--dangerously-skip-permissions` (tryb bez pytań) ma sens.

| Wariant | Co izoluje | Kiedy | Uwaga |
|---|---|---|---|
| devcontainer (referencyjny od Anthropic) | system plików hosta; sieć przez firewall z listą dozwolonych domen (`init-firewall.sh`) | dłuższa praca agenta bez nadzoru na laptopie | kontener widzi to, co zamontujesz: nie montuj `~/.aws` ani `~/.kube` |
| zwykły kontener / VM jednorazowa | jak wyżej, bez integracji z edytorem | eksperymenty, nieznane repo | po pracy kasujesz całość |
| dedykowany runner CI (np. GitHub Actions + `claude-code-action`) | osobna maszyna, krótkożyjący token, własna rola IAM | review PR, automatyczne poprawki, agent z dnia 3 | uprawnienia ustawiasz na tokenie i roli, nie w promptcie |
| osobne konto / rola w chmurze | zasięg zmian w infrastrukturze | agent z dostępem do AWS lub klastra | read-only ServiceAccount, jak w demie z serwerem MCP |

**Przykład dla runnera:** agent, który komentuje PR z Terraformem, dostaje token z `pull-requests: write` i `contents: read`, rolę IAM tylko do `terraform plan` i brak sekretów produkcyjnych w środowisku joba. Nawet jeśli prompt injection w opisie PR każe mu „zrób apply”, rola na to nie pozwoli.

---

## Porównanie zbiorcze

Im niżej w tabeli, tym mniej zależysz od modelu i od uwagi człowieka, ale tym więcej pracy przy konfiguracji.

| Warstwa | Kto egzekwuje | Obejście przez model | Pliki | Sieć | MCP | Koszt wdrożenia | Dobre do |
|---|---|---|---|---|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | model (prośba) | tak, jedno zdanie nacisku | prośba | prośba | prośba | minuty | konwencje, kontekst, nie bezpieczeństwo |
| tryb uprawnień | Claude Code + człowiek | nie, ale człowiek klika „tak” | edycja i Bash | WebFetch | tak | sekundy | tempo pracy na co dzień |
| `allow` / `ask` / `deny` | Claude Code | częściowo: skrypty i pełne ścieżki omijają reguły na pliki | Read/Edit + proste komendy | domeny w `WebFetch` | per narzędzie | minuty | stałe zakazy i zgody zespołu |
| hook `PreToolUse` | Twój skrypt | tylko tak, jak dobrze napiszesz skrypt | dowolna logika | dowolna logika | tak | godziny | reguły z warunkami, audyt, polityka firmy |
| sandbox | system operacyjny | nie w obrębie Basha | tak, dla Basha | tak, dla Basha | nie | minuty | domknięcie dziur deny, praca bez pytań |
| kontener / devcontainer | izolacja kontenera | tylko to, co zamontujesz | cały system | firewall | tak | godziny | agent bez nadzoru, nieznane repo |
| dedykowany runner + rola | infrastruktura i IAM | nie | cała maszyna | cała maszyna | tak | dzień | CI, auto-remediation, produkcja |
| managed settings | IT / MDM | nie, użytkownik nie nadpisze | jak reguły | jak reguły | jak reguły | wdrożenie w firmie | standard dla całej organizacji |

---

## Rekomendowane zestawy

| Sytuacja | Tryb | Reguły | Hooki | Sandbox | Izolacja |
|---|---|---|---|---|---|
| laptop, własne repo | `default` lub `acceptEdits` | deny na sekrety, allow na testy i odczyty | opcjonalnie log | tak | — |
| repo zespołu infrastruktury | `default` | `.claude/settings.json` w gicie: allow/ask/deny jak w przykładzie | blokada `apply`/`delete` | tak | kubeconfig read-only |
| CI (review PR, testy) | `dontAsk` | dokładne `--allowedTools` | log do artefaktu joba | tak | runner + krótki token |
| agent bez nadzoru (dzień 3) | `bypassPermissions` dopiero w kontenerze | deny dalej działa | blokada + audyt | tak | kontener / VM + rola tylko do odczytu |
| cała firma | `disableBypassPermissionsMode` | managed, `allowManagedPermissionRulesOnly` | managed, `allowManagedHooksOnly` | wymuszony | — |

## Podsumowanie i wniosek

- `CLAUDE.md` prosi model. Jedno zdanie nacisku wystarcza, żeby prośbę obejść, więc to nie jest zabezpieczenie.
- Tryb ustala, kiedy pytać. Komendy tylko do odczytu, np. `cat .env`, przechodzą w każdym trybie.
- `allow` / `ask` / `deny` blokują niezależnie od modelu, ale tylko to, co Claude Code rozpozna. Skrypt w Pythonie przejdzie.
- Hook dokłada logikę i audyt. Jego blokada wygrywa z `allow`, a jego zgoda nie zdejmuje `deny`.
- Sandbox zamyka Bash na poziomie systemu. Nie obejmuje Read, Edit ani MCP, więc działa w parze z regułami.
- Kontener, runner i rola IAM to jedyna warstwa, która nie ufa niczemu powyżej. Tylko tam `bypassPermissions` ma sens.

**Wniosek:** bezpieczeństwo agenta to suma warstw. Prośba w pliku instrukcji to kontekst, a granicę wyznaczają reguły, sandbox i uprawnienia poświadczeń. Im mniej człowiek patrzy na agenta, tym niższe warstwy muszą być włączone.
