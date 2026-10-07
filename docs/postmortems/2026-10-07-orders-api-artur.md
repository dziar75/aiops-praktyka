# Post-mortem: Niedostępność orders-api w namespace `artur` (szkic)

Data incydentu: 2026-10-07. Namespace: `artur`. Formuła blameless.

## Podsumowanie
`setup/check.sh` wykazał, że deployment `kantyna-orders-api` w namespace `artur` miał 0/2 gotowych podów, a testy funkcjonalne "menu przez web" i "zamówienie przez web" zwracały kod wyjścia 1. Dochodzenie wykazało, że w ConfigMapie `kantyna-flags` flagi `db_pool_leak` i `slow_menu_query` miały wartość `true`, co powodowało wyczerpywanie poola połączeń do Postgresa przez orders-api i nieudane readiness checki. Po wyłączeniu flag i restarcie deploymentu wszystkie 11/11 testów w `check.sh` przeszły.

## Wpływ
- **Zakres:** całkowita niedostępność funkcji zamówień i menu przez `web` w namespace `artur` (0/2 gotowych podów orders-api — nie częściowa degradacja, a pełny brak dostępnych instancji).
- **Czas trwania:** pody miały wiek ~75–78 minut w momencie wykrycia, z ciągłymi niepowodzeniami readiness probe (zdarzenie kubelet: 308 niepowodzeń w ostatnich 27 minutach okna zdarzeń) — rzeczywisty początek problemu mógł być wcześniejszy niż wiek obecnych podów (fakt: nieznany, patrz Pytania otwarte).
- **Inne komponenty:** `web`, `payments`, `worker`, `postgres` — bez zakłóceń (wszystkie gotowe, Postgres z normalnymi checkpointami w logach).

## Oś czasu

| Czas (UTC, przybliżony) | Zdarzenie |
|---|---|
| ok. 12:24 (wyliczone z AGE podów, niepewne) | Obecne pody `kantyna-orders-api-59df94c4dc-*` tworzone; od tego momentu readiness probe prawdopodobnie nie przechodzi |
| 13:34:29–13:39:16 | Logi aplikacji pokazują powtarzające się `"Readiness check failed", "error": "couldn't get a connection after 30.00 sec"` co ~5 s |
| ~13:39 | `setup/check.sh` zwrócony przez użytkownika: `8/11`, deployment orders-api `0/2`, testy menu/zamówienie: `exit code 1` |
| chwilę później | Diagnoza: `kubectl describe pod` → `Readiness probe failed: ... /readyz context deadline exceeded`; `kubectl logs` → błąd poola DB; `kubectl get configmap kantyna-flags` → `db_pool_leak: true`, `slow_menu_query: true`; Postgres zweryfikowany jako zdrowy |
| chwilę później | Patch ConfigMap: `db_pool_leak: false`, `slow_menu_query: false` |
| chwilę później | `kubectl rollout restart deployment/kantyna-orders-api -n artur` — rollout zakończony sukcesem, nowe pody `1/1 Running` w ~17 s / 11 s od utworzenia |
| chwilę później | Weryfikacja: `setup/check.sh` → `SUKCES: 11/11` |

## Przyczyna źródłowa
**Fakt:** ConfigMap `kantyna-flags` w klastrze miał `db_pool_leak: true` i `slow_menu_query: true` dla orders-api, podczas gdy domyślne wartości w `app/deploy/helm/kantyna/values.yaml` to `false` dla obu flag.

**Hipoteza (niepotwierdzona):** flagi te zostały ustawione na `true` ręcznie lub przez zewnętrzny skrypt/ćwiczenie — poza standardowym procesem Helm — ponieważ repo dokumentuje ten mechanizm jako celowe narzędzie do wstrzykiwania chaosu w ramach laboratoriów (`docs`/`CLAUDE.md`). Nie mamy dowodu, czy to był zamierzony scenariusz treningowy, czy nieodkreślona zmiana pozostała po innym ćwiczeniu.

**Luka systemowa:** stan ConfigMapu na klastrze mógł odbiegać (driftować) od wartości zdefiniowanych w `values.yaml` bez żadnego mechanizmu wykrywania tej rozbieżności (brak reconciliation/GitOps dla tego zasobu, lub brak widoczności dla tego, kto go ostatnio zmienił).

## Co zadziałało
- `setup/check.sh` szybko i precyzyjnie zlokalizował, który komponent i które przepływy użytkownika są zepsute.
- Zdarzenia Kubernetes (`kubectl describe pod`) jasno wskazały mechanizm awarii (readiness probe timeout na konkretnym endpoincie).
- Strukturalne logi JSON aplikacji od razu nazwały przyczynę techniczną (`couldn't get a connection after 30.00 sec`) bez potrzeby głębszego tracingu.
- Mechanizm hot-reload flag (ConfigMap) pozwolił naprawić problem bez rebuildu/push obrazu.
- Szybka pętla weryfikacji: ten sam `check.sh` natychmiast potwierdził naprawę end-to-end.

## Co nie zadziałało
- Problem nie został wykryty proaktywnie przez monitoring/alerting — ujawnił się tylko dzięki ręcznemu uruchomieniu `setup/check.sh`; nie sprawdzono, czy istniejąca reguła `KantynaDBPoolExhausted` w ogóle pokrywa ten namespace/scenariusz.
- Pody pozostawały w stanie `Running` z nieudanym readiness przez długi czas bez żadnego automatycznego mechanizmu samonaprawy (brak liveness probe/restartu wymuszonego przy trwałym wyczerpaniu poola).
- Brak widoczności/audytu, kto i kiedy zmienił ConfigMap `kantyna-flags` na wartości odbiegające od `values.yaml` — zmiana "poza systemem" nie została nigdzie zarejestrowana.
- Naprawiono obie flagi naraz, bez wcześniejszego wyizolowania, która z nich (`db_pool_leak` czy `slow_menu_query`) faktycznie powodowała brak gotowości podów.

## Akcje (właściciel, termin)

| Akcja | Właściciel | Termin |
|---|---|---|
| Sprawdzić, czy reguła `KantynaDBPoolExhausted` (i podobne) obejmuje namespace `artur`/wszystkie namespace trenujących, nie tylko `demo` | `<...>` | `<...>` |
| Ustalić proces/audyt zmian ConfigMapy `kantyna-flags` na klastrze (np. log zmian lub reconciliation z Helm) | `<...>` | `<...>` |
| Dodać do runbooka `KantynaDBPoolExhausted` wzmiankę o fladze `db_pool_leak` jako typowej przyczynie i sposobie szybkiej weryfikacji (`kubectl get configmap kantyna-flags -o jsonpath=...`) | `<...>` | `<...>` |
| Rozważyć dodanie health-checku/mechanizmu wymuszającego restart poda po przedłużonym niepowodzeniu readiness | `<...>` | `<...>` |
| Potwierdzić, czy ustawienie flag było zamierzonym ćwiczeniem — jeśli tak, oznaczyć to w dokumentacji laboratorium | `<...>` | `<...>` |

## Pytania otwarte
- Kto/co i kiedy ustawiło `db_pool_leak`/`slow_menu_query` na `true` w ConfigMapie — brak tego w `values.yaml`, więc zmiana nastąpiła poza standardowym deployem?
- Jak długo faktycznie trwała niedostępność przed wykryciem — wiek podów (75–78 min) mówi tylko o czasie od ostatniego restartu, nie wiadomo, czy wcześniejsze repliki miały ten sam problem dłużej?
- Czy obie flagi przyczyniły się do awarii, czy wystarczyłaby jedna — nie testowano ich osobno przed zastosowaniem łącznej naprawy?
- Czy istniał automatyczny alert pokrywający ten scenariusz, czy wykrycie zależało wyłącznie od ręcznego uruchomienia `setup/check.sh`?
