# lab02 — Debugging z AI: napraw Kantynę w swoim namespace

**Zasada:** najpierw dowód, potem zmiana. Każdą hipotezę AI potwierdzasz komendą, zanim cokolwiek zmienisz. Jedna zmiana naraz.

**Po labie masz:** działającą Kantynę (`setup/check.sh` → `SUKCES: 11/11`) i dziennik, w którym każda poprawka ma potwierdzoną przyczynę.

W Twoim namespace jest kilka awarii naraz. Naprawa jednej może odsłonić kolejną. To zamierzone.

## Zanim zaczniesz

- `kubectl` z dostępem do klastra (Twój namespace = Twój login)
- Claude Code z lab01 i komenda `/diagnoza` z lab01b (albo szablon `docs/prompts/diagnoza.md`)
- `k8sgpt` z kluczem LiteLLM ([`setup/README.md`](../../setup/README.md#5-k8sgpt), krok 5; klucz z karty)

Dzięki `.claude/settings.json` z repo agent może bez pytania czytać (`kubectl get/describe/logs`), a o każdą zmianę musi zapytać Ciebie.

## 1. Zobacz objawy

```bash
kubectl config set-context --current --namespace <login>
setup/check.sh
```

✅ `check.sh` pokazuje mniej niż 11/11. Zapisz, które testy nie przechodzą: to Twoja lista objawów.

## 2. Co widzą reguły, bez AI

`k8sgpt` bez `--explain` używa tylko wbudowanych reguł i nie wysyła niczego do modelu.

```bash
k8sgpt analyze --namespace <login>
```

Zanotuj, co znalazł. Porównasz to później z diagnozą AI.

## 3. Pętla diagnozy

Powtarzaj dla każdego objawu, po kolei:

1. **Hipotezy.** Claude Code w trybie planu (`Shift+Tab`):
   ```text
   /diagnoza <pierwszy objaw z check.sh>
   ```
2. **Weryfikacja.** Wybierz najbardziej prawdopodobną hipotezę i potwierdź ją komendą read-only. Wpisz wynik do dziennika (niżej).
3. **Poprawka.** Dopiero gdy hipoteza jest potwierdzona: jedna zmiana. Zanim zatwierdzisz komendę agenta, przeczytaj ją.
4. **Sprawdzenie.** `setup/check.sh`. Wynik wzrósł? Przejdź do następnego objawu.

## 4. Porównaj z k8sgpt

Dla jednego z naprawionych problemów:

```bash
k8sgpt analyze --namespace <login> --explain
```

Czy wyjaśnienie zgadza się z tym, co ustaliłeś?

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
