# lab01 — Rozgrzewka w Claude Code

**Zasada:** tylko pytasz, nic nie zmieniasz w kodzie. Wyjątek: `CLAUDE.md` i `.claude/settings.json`.

**Po labie masz:** Claude Code zalogowane kontem szkoleniowym, zablokowany odczyt sekretów i pierwszą odpowiedź AI, którą sam sprawdziłeś.

## Zanim zaczniesz

- sklonowany fork repo ([`setup/README.md`](../../setup/README.md), krok 0)
- zainstalowane Claude Code ([`setup/README.md`](../../setup/README.md#narzędzia-na-laptopie); Windows: w WSL2)
- konto szkoleniowe `uczNN@sages.io` (dane od prowadzącego)

## 1. Uruchom i sprawdź konto

```bash
cd aiops-praktyka
claude
```

Przy pierwszym uruchomieniu zaloguj się kontem szkoleniowym (otworzy się przeglądarka). Potem w sesji:

```text
/status
```

✅ Widzisz konto `uczNN@sages.io`, a nie konto prywatne ani klucz API.

Wpisz `/help`, żeby zobaczyć dostępne komendy. Potem naciskaj `Shift+Tab`, aż na dole pojawi się **plan mode**. W tym trybie agent tylko czyta pliki i proponuje plan, niczego sam nie zmienia. Zostań w nim do końca labu.

## 2. Daj agentowi kontekst: `CLAUDE.md`

`CLAUDE.md` to plik, który agent czyta na początku każdej sesji, czyli jego „instrukcja do projektu”.

```text
/init
```

Przeczytaj wygenerowany `CLAUDE.md` i dopisz ręcznie trzy rzeczy:
- wersje narzędzi (kubectl, Helm),
- komendę, którą sprawdzasz zmiany (np. `helm lint app/deploy/helm/kantyna`),
- jeden zakaz (np. „nie uruchamiaj `kubectl delete`”).

✅ `CLAUDE.md` istnieje i ma Twoje poprawki.

## 3. Zablokuj odczyt sekretów

Wszystko, co agent przeczyta, trafia do modelu. Plik `.env` nie może tam trafić.

Otwórz `.claude/settings.json`. Są w nim już reguły dla `kubectl` (przydadzą się w lab02):
- `allow`: agent robi to bez pytania,
- `ask`: pyta o zgodę,
- `deny`: nie wolno mu tego zrobić.

Dopisz do listy `deny`:

```json
"Read(./**/.env)", "Read(./**/*.tfstate)"
```

Wyjdź z sesji (`/exit`), uruchom `claude` jeszcze raz i zapytaj:

```text
Jakie zmienne są w app/.env?
```

✅ Agent nie może odczytać pliku. Jeśli zaproponuje `cat app/.env`, **odmów**, bo to obejście tej samej blokady.

## 4. Zadaj trzy pytania o repo

Wklejaj po kolei:

```text
Opisz strukturę tego repo i jak uruchomić aplikację. Podaj ścieżki plików. Niczego nie zmieniaj.
```

```text
Wyjaśnij app/scripts/backup-db.sh linia po linii. Wskaż 3 ryzyka i co się stanie, gdy jedna z komend się nie powiedzie.
```

```text
Co robi szablon Deployment orders-api w chartcie Helm? Co może pójść nie tak na produkcji? Odpowiedz w punktach, z numerami linii.
```

✅ Agent sam znajduje pliki i podaje konkretne ścieżki i linie.

## 5. Sprawdź jedną odpowiedź sam

Wybierz z odpowiedzi o `backup-db.sh` jedno twierdzenie i sprawdź je bez AI: otwórz plik albo uruchom

```bash
bash -n app/scripts/backup-db.sh
shellcheck app/scripts/backup-db.sh   # jeśli masz shellcheck
```

✅ Wiesz, czy agent miał rację, i umiesz to pokazać.

## SUKCES

- [ ] `/status` pokazuje konto szkoleniowe
- [ ] `CLAUDE.md` ma co najmniej jedną Twoją ręczną poprawkę
- [ ] reguła `deny` blokuje odczyt `.env`
- [ ] umiesz wskazać jedno twierdzenie agenta, które sprawdziłeś sam

## Dla chętnych

Zadaj pierwsze pytanie z kroku 4 w Copilot CLI albo w VS Code z Copilotem (jeśli masz licencję) albo w Claude Code w trybie domyślnym zamiast planu. Porównaj: kto sam czyta pliki, a kto pyta o zgodę?

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Nie masz forka (brak konta GitHub albo gita) | Załóż konto na https://github.com/signup, zainstaluj git, zrób krok 0 z `setup/README.md` |
| `claude: command not found` | Otwórz nowy terminal albo `source ~/.bashrc` |
| `/status` pokazuje konto prywatne albo klucz API | `/logout`, zaloguj się kontem szkoleniowym, nowa sesja. Sprawdź, czy profil powłoki nie ustawia `ANTHROPIC_API_KEY` |
| Reguła `deny` „nie działa” | Zrestartuj sesję. Plik musi być w `.claude/settings.json` w katalogu repo |
| Agent „nic nie robi” | Jest w trybie planu i czeka, aż zaakceptujesz plan |
| Błąd limitu zapytań | `/model` → mniejszy model, `/clear` między zadaniami, krótsze prompty |
| Firmowy VPN albo proxy blokuje połączenie | Zgłoś prowadzącemu |
