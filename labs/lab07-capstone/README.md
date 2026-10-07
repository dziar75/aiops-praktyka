# lab07 — Capstone: pełny incydent z AI

**Zasada:** dowód przed zmianą, zmiana przez repo, post-mortem bez zgadywania.

**Po labie masz:** samodzielnie przeprowadzony incydent, od zgłoszenia użytkownika do post-mortem, z naprawą wdrożoną przez Twój pipeline.

## Zgłoszenie

> Użytkownicy piszą, że menu ładuje się bardzo wolno, a czasem dostają błąd. Przeprowadź incydent: od pierwszego komunikatu do post-mortem. Każdą hipotezę AI potwierdź danymi.

## Zanim zaczniesz

- Kantyna w Twoim namespace wdrożona przez pipeline z lab03 (ostatni przebieg na `main` zielony)
- Claude Code, `kubectl`, Grafana z dashboardem z lab05
- szablony `docs/prompts/komunikat-incydentu.md`, `diagnoza.md`, `post-mortem.md` i runbooki w `app/runbooks/`

Załóż dziennik incydentu, plik `incydent.md` w swoim forku:

| Godzina | Hipoteza (AI / ja) | Komenda / zapytanie | Wynik | Status |
|---|---|---|---|---|

Wszystko, co robisz, wpisuj do niego na bieżąco. Z niego powstanie post-mortem.

## 1. Wykrycie

```bash
setup/check.sh
```

Otwórz też dashboard z lab05. Zapisz godzinę i pierwsze objawy. To początek osi czasu.

✅ W dzienniku jest godzina startu i lista objawów.

## 2. Pierwszy komunikat

Poproś agenta o pierwszą wiadomość na kanał zespołu według `docs/prompts/komunikat-incydentu.md`: co wiemy, jaki jest wpływ, kiedy następna aktualizacja. Popraw ją i wklej do dziennika.

✅ Komunikat nie obiecuje niczego, czego jeszcze nie wiesz.

## 3. Diagnoza z AI

Claude Code w trybie planu, szablon `docs/prompts/diagnoza.md` i pasujący runbook z `app/runbooks/`. Każdą hipotezę wpisz do dziennika razem z dowodem.

Przyczyn może być więcej niż jedna.

✅ Każda przyczyna w dzienniku ma dowód (komendę albo zapytanie i jego wynik).

## 4. Mitygacja i naprawa

1. **Mitygacja:** najpierw przywróć działanie usługi, nawet jeśli przyczyna jeszcze zostaje.
2. **Naprawa:** usuń przyczynę **commitem w swoim forku**. Wdroży go Twój pipeline z lab03.
3. Zanim zrobisz commit, przejrzyj diff (`git diff`).

Wpisz do dziennika SHA commita i link do przebiegu.

✅ Przebieg z naprawą jest zielony.

## 5. Weryfikacja

```bash
setup/check.sh
```

✅ `check.sh` → 11/11, a metryki na dashboardzie wróciły do poziomu sprzed incydentu i trzymają się tam przez 5 minut.

## 6. Post-mortem

Poproś agenta o szkic post-mortem z dziennika (`docs/prompts/post-mortem.md`). Potem:
- oznacz wszystko, co AI dopisało bez dowodu w dzienniku,
- dopisz akcje zapobiegawcze.

✅ W post-mortem widać, co napisało AI, a co poprawiłeś Ty.

## SUKCES

- [ ] `setup/check.sh` → `SUKCES: 11/11`, metryki stabilne przez 5 min
- [ ] naprawa weszła commitem przez pipeline (link do przebiegu w dzienniku)
- [ ] post-mortem ma oś czasu, każdą przyczynę potwierdzoną dowodem i co najmniej jedną akcję zapobiegawczą
- [ ] w post-mortem widać, co napisało AI, a co poprawiłeś

## Dla chętnych

- Dodaj do pipeline'u skan obrazu Trivy przed pushem do ECR (akcja przypięta do SHA, build przerywa się na `CRITICAL`).
- Puść agenta z lab06 jako „pierwszą linię” na tym incydencie i porównaj jego wnioski ze swoimi.

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Pipeline czerwony na kroku AWS/ECR | To samo co w lab03: `permissions`, rola, gałąź `main` |
| Pipeline czerwony z `conflict with "kubectl-patch"` | To nie awaria CI. Przeczytaj komunikat: który obiekt, które pole, kto je zmienił. Porównaj repo z tym, co jest na klastrze, i zdecyduj, co ma zostać. Nie dopisuj `--force-conflicts` do workflow |
| Brak danych na dashboardzie | Sprawdź namespace i zakres czasu w Grafanie |
| `budget exceeded` | Zgłoś prowadzącemu |
