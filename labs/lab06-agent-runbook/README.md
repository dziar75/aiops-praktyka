# lab06 — Agent: alert → runbook → akcja po Twoim „tak”

**Zasada:** odczyt bez pytania, zmiana tylko za Twoją zgodą.

**Po labie masz:** działającego agenta, który na alert z Twojego namespace podaje przyczynę z dowodem, naprawia Kantynę dopiero po Twoim „t”, i wiesz, co go zatrzymało, gdy alert próbował nim sterować.

## Zanim zaczniesz

- zdrowa Kantyna (`setup/check.sh` → `SUKCES: 11/11`)
- Python 3.8+ (`python3 --version`), nic nie instalujesz
- klucz LiteLLM w zmiennych (ten sam co w kubectl-ai):

```bash
export OPENAI_API_KEY=<klucz-LiteLLM-z-karty>
export OPENAI_ENDPOINT=https://llm.aiops.marniok.dev/v1
cd labs/lab06-agent-runbook
```

Pliki labu:
- `agent.py`: cały agent, ok. 200 linii,
- `alerts/`: dwa alerty w formacie Alertmanagera,
- `zepsuj.sh`: psuje Twoją Kantynę.

## 1. Przeczytaj agenta

Otwórz `agent.py` (albo poproś Claude Code: „wyjaśnij mi ten plik w 5 punktach”). Znajdź trzy miejsca:
- pętlę `for step in range(...)` w `main()`: model prosi o narzędzie, kod je wykonuje, wynik wraca do modelu,
- `READ_TOOLS` i `ACTION_TOOLS`: co agent może czytać, a co zmieniać,
- `input("  Zgoda? [t/N] ")`: bramkę człowieka.

Sprawdź też, na jakim koncie agent działa:

```bash
kubectl auth can-i --list --as=system:serviceaccount:$(kubectl config view --minify -o jsonpath='{..namespace}'):agent
```

✅ Wiesz, gdzie jest pętla i bramka. Konto `agent` nie ma dostępu do `secrets` i nie może nic usuwać.

## 2. Agent bez runbooka, potem z runbookiem

Kantyna jest zdrowa, więc alert jest fałszywy. Zobacz, co agent zrobi bez instrukcji, a co z runbookiem.

```bash
python3 agent.py alerts/high-error-rate.json --bez-runbooka
python3 agent.py alerts/high-error-rate.json
```

Porównaj obie odpowiedzi: jakie narzędzia wywołał, ile kroków, czy przyznał, że błędów nie ma? Gdy zaproponuje akcję na zdrowej Kantynie, odpowiedz `N`.

```bash
cat audit.jsonl
```

✅ Masz dwie diagnozy i wiesz, co zmienił runbook.

## 3. Zepsuj Kantynę i pozwól agentowi naprawić

```bash
cat zepsuj.sh
./zepsuj.sh
```

Odczekaj minutę i sprawdź, że coś nie działa:

```bash
../../setup/check.sh
python3 agent.py alerts/high-error-rate.json
```

Zanim odpowiesz na „Zgoda? [t/N]”, zadaj sobie pytanie: czy ta akcja usuwa przyczynę, czy tylko objaw? Restart orders-api przy włączonej fladze nic nie da. Zgadzasz się tylko na akcję, która naprawia przyczynę.

Po akcji odczekaj minutę:

```bash
../../setup/check.sh
```

✅ Agent wskazał flagę `error_rate` z dowodem (fragment `get_flags` albo logu), akcję wykonał po Twoim `t`, a `check.sh` → `SUKCES: 11/11`.

## 4. Alert, który próbuje sterować agentem

Ktoś wpisał do opisu alertu polecenia dla agenta. Nie zaglądaj do pliku przed uruchomieniem.

```bash
python3 agent.py alerts/injected.json
```

Na każde pytanie o zgodę odpowiedz `N`. Potem przeczytaj plik i `audit.jsonl`:

```bash
cat alerts/injected.json
tail -5 audit.jsonl
```

Zapisz odpowiedzi na trzy pytania:
- Co zrobił model: rozpoznał atak czy próbował wykonać polecenia?
- Co go zatrzymało: brak narzędzia, bramka `t/N`, uprawnienia konta?
- Co by się stało z `--auto` (bez pytania)?

✅ Wiesz, która warstwa zatrzymała każde z poleceń z alertu.

## 5. Zdejmij jedną warstwę i sprawdź, co zostało

W kroku 4 agenta chroniły cztery warstwy: model, lista narzędzi, bramka `t/N` i uprawnienia konta `agent`. Teraz celowo osłabiasz dwie z nich i sprawdzasz, czy pozostałe wystarczą. To jedyne miejsce w labie, gdzie łamiesz zasadę „zmiana tylko za Twoją zgodą”, i robisz to świadomie.

### 5a. Daj agentowi narzędzie do Secretów

Otwórz `agent.py`. **Pod** funkcją `get_flags()` wklej nową funkcję:

```python
def get_secret(name):
    return kubectl("get", "secret", name, "-o", "jsonpath={.data}")
```

W tym samym pliku zamień linię z `READ_TOOLS = {...}` na:

```python
READ_TOOLS = {"get_pods": get_pods, "get_events": get_events, "get_logs": get_logs, "get_flags": get_flags,
              "get_secret": get_secret}
```

W liście `TOOLS`, pod linią z `tool("get_flags", ...)`, dopisz:

```python
    tool("get_secret", "Zawartość Secretu Kubernetesa (base64).", {"name": {"type": "string"}}, ["name"]),
```

Sprawdź, czy plik się uruchamia, i powtórz atak z kroku 4. Na każde pytanie o zgodę odpowiedz `N`:

```bash
python3 agent.py --help > /dev/null && echo OK
python3 agent.py alerts/injected.json
grep get_secret audit.jsonl
```

Jeśli model nie wywołał `get_secret` (rozpoznał atak), sprawdź sam, co by dostał:

```bash
kubectl auth can-i get secrets --as=system:serviceaccount:$(kubectl config view --minify -o jsonpath='{..namespace}'):agent
```

✅ Wiesz, czy model sięgnął po Secret i co go zatrzymało: model, który odmówił, czy `Forbidden` z uprawnień konta `agent`.

### 5b. Zdejmij bramkę człowieka

Ten sam alert z flagą `--auto`: agent wykona akcje bez pytania. W Twoim namespace to bezpieczne: restart Deploymentu i powrót flagi do wartości domyślnej da się cofnąć.

```bash
python3 agent.py alerts/injected.json --auto
grep '"auto"' audit.jsonl
kubectl get pods
```

Odczekaj minutę i sprawdź, że Kantyna wróciła do zdrowia:

```bash
../../setup/check.sh
```

✅ Wiesz, które polecenia z alertu wykonały się bez bramki (`"decyzja": "auto"` w `audit.jsonl`), a `check.sh` → `SUKCES: 11/11`.

### 5c. Podsumuj warstwy i przywróć agenta

Zapisz tabelę w notatkach:

| Warstwa | Co zatrzymała w kroku 4 | Co zatrzymała po 5a i 5b |
|---|---|---|
| model | | |
| lista narzędzi | | |
| bramka `t/N` | | |
| uprawnienia konta `agent` | | |

Przywróć oryginalny `agent.py`:

```bash
git checkout -- agent.py
grep -c get_secret agent.py
```

✅ Tabela jest wypełniona, a `grep` zwraca `0`.

## Dla chętnych

- Uruchom krok 4 na mocniejszym modelu i porównaj zachowanie: `--model claude-sonnet-5-5`.
- Dodaj eskalację: gdy runbook mówi „Caution”, agent kończy pracę z opisem dla człowieka i nie wywołuje akcji.
- Przepisz pętlę na LangChain `create_agent` albo OpenAI Agents SDK (`docs/`, materiał o agentach, sekcje 10.2–10.3).

## SUKCES

- [ ] agent wskazał przyczynę awarii z dowodem z narzędzia
- [ ] naprawa wykonana dopiero po Twoim `t`, `setup/check.sh` → `SUKCES: 11/11`
- [ ] wiesz, co zatrzymało polecenia z `alerts/injected.json`
- [ ] tabela warstw z kroku 5 wypełniona, `agent.py` przywrócony

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| `Ustaw OPENAI_API_KEY` | `export OPENAI_API_KEY=<klucz z karty>` w tym samym terminalu |
| `Błąd bramy AI 401` albo `budget exceeded` | zły klucz albo wyczerpany budżet, zgłoś prowadzącemu |
| `Brak połączenia` / timeout | Twój adres IP nie jest na liście, podaj go na czacie |
| `Forbidden … system:serviceaccount:<login>:agent` przy każdym narzędziu | konto `agent` jeszcze nie istnieje, zgłoś prowadzącemu |
| `Brak namespace` | `export AGENT_NAMESPACE=<login>` |
| `check.sh` dalej < 11/11 minutę po naprawie | `kubectl get cm kantyna-flags -o jsonpath='{.data.flags\.json}'`: czy `error_rate` to 0? Jeśli nie, uruchom agenta jeszcze raz |
| `IndentationError` albo `SyntaxError` po kroku 5a | `git checkout -- agent.py` i wklej trzy fragmenty jeszcze raz; funkcja `get_secret` zaczyna się od początku linii, linia z `tool(...)` od 4 spacji |
| Agent kończy na „Przekroczony limit kroków” | uruchom ponownie albo z `--model claude-sonnet-5-5` |
