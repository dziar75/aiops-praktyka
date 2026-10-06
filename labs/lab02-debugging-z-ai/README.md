# lab02 — Debugging z AI: napraw Kantynę w swoim namespace

**Zasada:** najpierw dowód, potem zmiana. Każdą hipotezę AI potwierdzasz komendą, zanim cokolwiek zmienisz. Jedna zmiana naraz.

**Po labie masz:** działającą Kantynę (`setup/check.sh` → `SUKCES: 11/11`) i dziennik, w którym każda poprawka ma potwierdzoną przyczynę.

Prowadzący zepsuł Kantynę w Twoim namespace przed labem: nic nie musisz psuć sam. Awarii jest kilka naraz, a naprawa jednej może odsłonić kolejną. To zamierzone.

## Zanim zaczniesz

- `kubectl` z dostępem do klastra (Twój namespace = Twój login)
- Claude Code uruchomione z katalogu Twojego forka
- komenda `/diagnoza`, którą zapisałeś w lab01b (część C) w `.claude/commands/diagnoza.md`. Nie masz jej? Skopiuj blok z `docs/prompts/diagnoza.md` do tego pliku, w miejsce objawu wpisz `$ARGUMENTS` i uruchom nową sesję `claude`
- `k8sgpt` z kluczem LiteLLM ([`setup/README.md`](../../setup/README.md#5-k8sgpt), krok 5; klucz z karty)

Dzięki `.claude/settings.json` z repo agent może bez pytania czytać (`kubectl get/describe/logs`), a o każdą zmianę musi zapytać Ciebie.

## 1. Zobacz objawy

```bash
kubectl config set-context --current --namespace <login>
setup/check.sh
```

✅ `check.sh` pokazuje mniej niż 11/11. Każda linia z ❌ to jeden objaw. Przepisz je do dziennika (tabela na dole).

Pokazuje `SUKCES: 11/11`? Napisz na czat, prowadzący jeszcze nie włączył awarii.

Załóż dziennik:

```bash
mkdir -p lab02
```

## 2. Co widzą reguły, bez AI

`k8sgpt` bez `--explain` używa tylko wbudowanych reguł i nie wysyła niczego do modelu.

```bash
k8sgpt analyze --namespace <login>
```

Zanotuj, co znalazł. Wybierz jeden znaleziony problem i poproś o wyjaśnienie modelu **teraz, przed naprawą** (po naprawie k8sgpt już go nie zobaczy):

```bash
k8sgpt analyze --namespace <login> --explain
```

Zapisz wyjaśnienie. Porównasz je w kroku 4 z tym, co ustalisz sam.

## 3. Pętla diagnozy

Powtarzaj dla każdego objawu, po kolei:

1. **Hipotezy.** Nowa sesja `claude` (albo `/clear`), `Shift+Tab` aż do **plan mode**. Jako argument wklej linię z ❌ z `check.sh`:
   ```text
   /diagnoza <linia z ❌ z check.sh>, namespace <login>
   ```
   Agent sam zbiera dane (`kubectl get/describe/logs`) i zwraca tabelę hipotez.
2. **Weryfikacja.** Wybierz najbardziej prawdopodobną hipotezę i uruchom jej komendę weryfikującą sam, w swoim terminalu. Wynik wpisz do dziennika.
3. **Poprawka.** Dopiero gdy hipoteza jest potwierdzona: `Shift+Tab` do trybu domyślnego i poproś o jedną zmianę. Agent zapyta o zgodę na `kubectl set/patch/rollout`: przeczytaj komendę, zanim ją zatwierdzisz.
4. **Sprawdzenie.** `setup/check.sh`. Wynik wzrósł? Wróć do kroku 1 z następną linią z ❌.

## 4. Porównaj z k8sgpt

Weź wyjaśnienie k8sgpt z kroku 2 i porównaj je z wierszem dziennika dla tego samego problemu. Czy przyczyna się zgadza? Co k8sgpt pominął, a co znalazłeś Ty z agentem?

## 5. Podsumuj

Dopisz w dzienniku, która sugestia AI była błędna albo wymagała uprawnień, których nie masz, i dlaczego jej nie wdrożyłeś.

## Dziennik diagnozy

Skopiuj tabelę do pliku `lab02/dziennik.md` w swoim forku.

| # | Objaw | Hipoteza (kto: AI / ja / k8sgpt) | Komenda weryfikująca | Wynik | Status | Poprawka |
|---|-------|----------------------------------|----------------------|-------|--------|----------|
| 1 |       |                                  |                      |       | ✅/❌  |          |

## SUKCES

- [ ] `setup/check.sh` kończy się `SUKCES: 11/11`
- [ ] każda poprawka ma w dzienniku wiersz z potwierdzoną przyczyną
- [ ] umiesz wskazać co najmniej jedną sugestię AI, której **nie** wdrożyłeś, i powiedzieć dlaczego

## Dla chętnych

- Dodatkowa awaria, jeśli prowadzący ją włączył.
- Poproś Claude Code o szkic post-mortem z dziennika (`docs/prompts/post-mortem.md`).

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| `Forbidden` przy `kubectl get` | Zły kontekst albo namespace. Sprawdź `kubectl auth can-i --list -n <login>` |
| `k8sgpt --explain` nie odpowiada | `k8sgpt auth list` (backend `litellm`). Przy timeoucie zgłoś prowadzącemu swój adres IP |
| `budget exceeded` | Zgłoś prowadzącemu |
| Po kilku zmianach naraz `check.sh` spadł | `kubectl rollout history` / `kubectl rollout undo`, potem jedna zmiana naraz |
| Błąd limitu zapytań w Claude Code | `/model` → mniejszy model, `/clear` między awariami, przycinaj logi |
