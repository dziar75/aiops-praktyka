# lab01b — Prompt, który da się sprawdzić

**Zasada:** nic nie zmieniasz na klastrze (walidacja tylko przez `--dry-run`), a do modelu nie trafia żaden sekret.

**Po labie masz:** dwa prompty sprawdzone narzędziem i danymi oraz własną komendę `/diagnoza`, z której skorzystasz w lab02.

## Zanim zaczniesz

- Claude Code skonfigurowane w lab01, uruchamiane z katalogu forka
- `kubectl` z dostępem do klastra (Twój namespace = Twój login)
- najnowsza wersja repo. Jeśli nie widzisz katalogu `labs/lab01b-prompty/`, zrób `git pull upstream main`.

W katalogu repo utwórz katalog na wyniki:

```bash
mkdir -p lab01b
```

Przydadzą się szablony promptów z `docs/prompts/` i chart Kantyny w `app/deploy/helm/kantyna/`.

## Część A: konfiguracja, którą sprawdza walidator

### A1. Zły prompt

Nowa sesja `claude`. Wklej prompt bez zmian:

```text
Napisz mi Deployment dla orders-api, żeby działał na produkcji. Zapisz go do lab01b/zly.yaml.
```

### A2. Dobry prompt z szablonu

Otwórz `docs/prompts/generowanie-konfiguracji.md` i wypełnij szablon. Zamiast samemu wklejać kontekst, każ agentowi go zebrać:
- „przeczytaj `app/deploy/helm/kantyna/values.yaml` i szablon `deployment-orders-api.yaml`”,
- „wersję klastra sprawdź przez `kubectl version`”.

Dopisz wymagania:
- nazwa `orders-api-lab`,
- obraz i zasoby takie jak w chartcie,
- hasło do bazy z istniejącego Secretu (nazwa z chartu), nie wpisane jawnie,
- wynik zapisz do `lab01b/dobry.yaml`.

### A3. Walidacja na serwerze

`--dry-run=server` wysyła plik do serwera API, który sprawdza schemat i uprawnienia, ale niczego nie tworzy.

```bash
kubectl apply --dry-run=server -n <login> -f lab01b/zly.yaml
kubectl apply --dry-run=server -n <login> -f lab01b/dobry.yaml
```

✅ `dobry.yaml` przechodzi. Błąd przy `zly.yaml` to też dobry wynik, bo walidator złapał coś, co wymyślił model.

### A4. Notatki

W `lab01b/notatki.md` zapisz trzy różnice między plikami i **jedną rzecz, której walidator nie sprawdził** (np. czy limity pamięci mają sens).

## Część B: diagnoza, którą sprawdzają dane

Plik `labs/lab01b-prompty/dane/awaria.txt` to zrzut z awarii innej Kantyny, nie Twojego namespace.

### B1. Usuń sekrety, zanim cokolwiek trafi do modelu

Przeczytaj plik sam (bez agenta). Potem zamaskuj sekrety i sprawdź wynik:

```bash
perl -pe 's/(password|token|secret)=\S+/$1=***REDACTED***/gi' \
  labs/lab01b-prompty/dane/awaria.txt > lab01b/awaria-zred.txt
grep -n -i -E 'pass|token|secret|@' lab01b/awaria-zred.txt
```

✅ W `awaria-zred.txt` nie ma żadnego hasła ani tokenu. Jeśli coś zostało, popraw polecenie i uruchom je jeszcze raz.

### B2. Diagnoza z szablonu

Wypełnij szablon `docs/prompts/diagnoza.md`. W polu „Dane” wskaż **tylko** plik `lab01b/awaria-zred.txt`. Oczekiwany format odpowiedzi to tabela: `hipoteza · dowód z danych · komenda weryfikująca`.

### B3. Sprawdź dowody

Każdy „dowód” z tabeli znajdź w pliku:

```bash
grep -n "<fragment dowodu>" lab01b/awaria-zred.txt
```

Dowód, którego nie ma w danych, to **halucynacja**. Zapisz ją w notatkach. Sprawdź też, czy agent poprosił o dane, których brakuje.

### B4. Powtarzalność

Wpisz `/clear` i wklej ten sam prompt jeszcze raz. Czy kolejność hipotez i dowody są takie same?

## Część C: prompt jako komenda

### C1. Własna komenda `/diagnoza`

Każdy plik w `.claude/commands/` to komenda Claude Code. `$ARGUMENTS` zostanie zastąpione tym, co wpiszesz po nazwie komendy.

Zapisz swój najlepszy prompt diagnozy w `.claude/commands/diagnoza.md`. W miejscu objawu wpisz `$ARGUMENTS` i dopisz:

```text
Zbierz dane komendami read-only (kubectl get/describe/logs). Zredaguj sekrety przed analizą.
```

### C2. Test

Nowa sesja `claude`, potem:

```text
/diagnoza kantyna-postgres-0 Pending, dane w lab01b/awaria-zred.txt
```

✅ Komenda się uruchamia i pracuje na pliku. Testuj ją tylko na tym pliku, **nie** na swoim namespace.

## SUKCES

- [ ] `dobry.yaml` przechodzi `kubectl apply --dry-run=server`, a Ty wiesz, czego walidator nie sprawdził
- [ ] do modelu nie trafił żaden sekret z `awaria.txt`
- [ ] każdy dowód w tabeli diagnozy znalazłeś w danych albo oznaczyłeś jako halucynację
- [ ] `/diagnoza` działa w nowej sesji

## Dla chętnych

- Zrób część B przez `claude -p` z `--output-format json` zamiast tabeli, a wynik sprawdź `jq`. Dlaczego do skryptu lepszy jest JSON?
- Dopisz do `/diagnoza` przykład dobrej odpowiedzi (few-shot). Czy odpowiedzi są bardziej powtarzalne?

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| `--dry-run=server` zwraca `Forbidden` | Sprawdź `-n <login>`. W cudzym namespace nie masz uprawnień |
| `unknown field` albo `strict decoding error` | Walidator zadziałał: model wymyślił pole. Zapisz to w notatkach |
| Claude Code pyta o zgodę na `kubectl apply` | To reguła `ask` z `.claude/settings.json`. Zatwierdź tylko z `--dry-run=server` |
| `/diagnoza` nie pojawia się w podpowiedziach | Plik musi być w `.claude/commands/` w katalogu repo. Uruchom nową sesję |
| Agent sam czyta `dane/awaria.txt` (wersję bez redakcji) | Odmów i wskaż `lab01b/awaria-zred.txt`. To ten sam przypadek co `cat app/.env` w lab01 |
