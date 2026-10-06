# GitHub Actions: tag czy SHA — skąd pipeline bierze cudzy kod

Materiał pomocniczy do szkolenia „AIOps w praktyce” (dzień 2, tematy 2.1 i 2.2). Diagram architektury: [`architektura.html`](architektura.html).

> Stan na 6 października 2026. SHA w przykładach sprawdzone tego dnia przez `git ls-remote`.

---

## TL;DR

| | **Tag** (`@v4`, `@v4.2.0`) | **SHA** (`@93cb6ef…` 40 znaków) |
|---|---|---|
| **Czym jest** | Nazwa wskazująca na commit — wskaźnik, który można przestawić | Hash zawartości commita — identyfikator samego kodu |
| **Czy może się zmienić** | Tak: `git tag -f` + `git push -f` (major `v4` przesuwa się celowo przy każdym wydaniu) | Nie: inny kod = inny hash |
| **Co dostajesz przy przebiegu** | To, na co tag wskazuje **w tej chwili** | Zawsze ten sam kod |
| **Kto może Ci podmienić kod** | Każdy, kto ma prawo push tagów w repo akcji (maintainer, bot, włamywacz) | Nikt |
| **Wygoda** | Czytelne, aktualizacje „same” | Nieczytelne → komentarz `# v5.0.1` + Dependabot |

**Najkrócej:** każda akcja w `uses:` to cudzy kod uruchamiany z Waszymi sekretami. Tag oznacza zaufanie, że nikt go nie przestawi. SHA tego zaufania nie wymaga.

---

## 1. Podstawy: co się dzieje, gdy pipeline startuje

### Akcja to po prostu repo na GitHubie

```yaml
steps:
  - uses: actions/checkout@v4
```

- `actions/checkout` = repo `github.com/actions/checkout` (właściciel `actions`, nazwa `checkout`).
- `@v4` = **ref**, czyli którą wersję tego repo pobrać: tag, gałąź albo SHA.
- Akcja to kod (najczęściej JavaScript, czasem kontener Dockera albo skrypt „composite”), który runner uruchamia jako krok joba.

### Co robi `actions/checkout`

Najpopularniejsza akcja świata — jest w niemal każdym workflow. Klonuje **Wasze** repo na runner (do katalogu roboczego), żeby kolejne kroki miały na czym pracować: testy, build obrazu, `helm upgrade`. Bez niej runner jest pustą maszyną.

Szczegół, który wraca w bezpieczeństwie: domyślnie (`persist-credentials: true`) checkout zostawia `GITHUB_TOKEN` w `.git/config`, żeby późniejsze kroki mogły zrobić `git push`. Każdy kolejny krok — także cudza akcja — może go stamtąd odczytać. Stąd zalecenie `persist-credentials: false` (zizmor zgłasza to jako `artipacked`).

### Co znaczy `@v5` i czyja to numeracja

**To numeracja akcji, nie Waszego repo.** `actions/checkout` to osobne repo (`github.com/actions/checkout`), utrzymywane przez zespół GitHuba. `v5` to tag w **ich** repo — oni go tworzą i przestawiają. Wy w workflow tylko wybieracie, którą ich wersję pobrać. Wasze repo może mieć własne tagi (np. `v1.0.0` Kantyny), ale to zupełnie niezależny zestaw.

> Analogia: `uses: actions/checkout@v5` działa jak `FROM python:3.12` w Dockerfile albo `requests==2.32` w `requirements.txt`. Numer należy do tego, co pobieracie, a nie do Waszego projektu.

**Skąd ten numer — wersjonowanie semantyczne** (`MAJOR.MINOR.PATCH`, np. `5.1.0`):

| Część | Kiedy rośnie | Przykład |
|---|---|---|
| MAJOR (`5`) | zmiana, która może coś zepsuć | nowa wersja Node, usunięta opcja |
| MINOR (`.1`) | nowa funkcja, wstecznie zgodna | nowa opcja w `with:` |
| PATCH (`.0`) | poprawka błędu | naprawiony bug |

**Przy każdym wydaniu maintainer robi dwie rzeczy:**

1. tworzy tag konkretnej wersji, np. `v5.1.0` (zasadniczo się nie zmienia),
2. **przestawia tag „major” `v5`** na ten sam commit.

To konwencja zalecana przez GitHuba autorom akcji: użytkownik pisze `@v5` i sam dostaje poprawki z linii 5.x, bez zmiany workflow. Wygodne — i z tego samego powodu ryzykowne: **`v5` jest zaprojektowany tak, żeby się przesuwał**. Obok `v5` istnieją równolegle `v6` i `v7` (6.10.2026 najnowsza to `v7.0.1`), więc `@v5` to nie „najnowsza wersja”, tylko „najnowsza z piątki”.

**Skąd ludzie biorą ten numer:**

- README akcji albo GitHub Marketplace — przykład użycia,
- zakładka *Releases* w repo akcji — lista wydań z changelogami,
- z pamięci albo od AI — stąd stare wersje: model pisze `@v4`, bo tak wyglądała większość workflow, na których się uczył.

**Jednym zdaniem:** *„`v5` to nie numer zapisany na stałe, tylko etykieta »najnowsze z piątki« w repo autora akcji. Autor przestawia ją przy każdym wydaniu — więc może ją przestawić też ktoś, kto przejmie jego konto.”*

### Krok po kroku: start joba

1. Zdarzenie (push, PR) uruchamia workflow, GitHub przydziela runner (świeża maszyna wirtualna).
2. Runner czyta `uses:` i **rozwiązuje ref**: pyta GitHuba „na jaki commit wskazuje dziś `actions/checkout@v4`?”.
3. Pobiera kod akcji z tego commita. W logu joba widać to w sekcji *Set up job*:
   `Download action repository 'actions/checkout@v4' (SHA:11d5960a326750d5838078e36cf38b85af677262)`
4. Uruchamia akcję. Akcja działa **w tym samym jobie co reszta kroków**: widzi zmienne środowiskowe, sekrety przekazane do joba, `GITHUB_TOKEN`, pliki z checkoutu, poświadczenia AWS po OIDC.
5. Przy następnym przebiegu cała procedura od nowa — punkt 2 może dać **inny commit**.

> Akcja nie jest „wtyczką w piaskownicy”. To kod uruchomiony z pełnymi uprawnieniami joba.

---

## 2. Tag, gałąź, SHA — trzy sposoby wskazania wersji

| Zapis | Co to jest | Jak się zmienia |
|---|---|---|
| `@main` | gałąź | z każdym commitem do `main` — najgorsza opcja |
| `@v4` | tag „major” | maintainer **celowo** przestawia go przy każdym wydaniu v4.x |
| `@v4.2.0` | tag konkretnej wersji | „nie powinien” się zmieniać — ale technicznie może |
| `@11d5960a…` (40 znaków) | SHA commita | nie zmienia się nigdy |

### Dlaczego tag da się przestawić

W gicie tag to plik z jedną linią: „ta nazwa → ten commit”. Przestawienie to dwie komendy:

```bash
git tag -f v4 <inny-commit>
git push -f origin v4
```

Nie zostaje po tym ślad w historii repo, który zauważyłby użytkownik akcji. Nikt nie dostaje powiadomienia.

### Dowód z dzisiaj (6.10.2026)

```bash
git ls-remote https://github.com/actions/checkout 'refs/tags/v5*'
```
```
fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09  refs/tags/v5
08c6903cd8c0fde910a37f88322edcfb5dd907a8  refs/tags/v5.0.0
93cb6efe18208431cddfb8368fd83d5badbf9bfd  refs/tags/v5.0.1
fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09  refs/tags/v5.1.0
```

`v5` wskazuje dziś na ten sam commit co `v5.1.0`. Przy wydaniu v5.0.1 wskazywał na v5.0.1. **Tag major przesuwa się z definicji** — i dokładnie tego mechanizmu używa napastnik.

### Czym jest SHA

**SHA** (*Secure Hash Algorithm*; czyta się „sza”, w praktyce mówi się też po prostu „hash commita”) to hash (skrót kryptograficzny) zawartości commita: plików, autora, daty i SHA rodzica. Zmiana choćby jednego bajtu daje zupełnie inny hash. Dlatego `@93cb6efe…` oznacza „dokładnie ten kod” i nic innego pod tą nazwą się nie pojawi.

---

## 3. W czym problem: atak przez przestawienie tagu

Zobacz diagram w [`architektura.html`](architektura.html).

**Najpierw kierunek, bo łatwo go pomylić:** akcja nie zabiera Waszego kodu ani sekretów „do siebie”. Jest odwrotnie — **jej kod przychodzi do Was**. Runner pobiera kod akcji i uruchamia go w Waszym jobie, na Waszej maszynie. Tam akcja widzi to samo co każdy inny krok: sekrety joba, `GITHUB_TOKEN`, poświadczenia chmury, pliki repo. Jeśli to kod napastnika, sam odczytuje sekrety na miejscu i sam wysyła je na zewnątrz.

> Akcja to nie zewnętrzna usługa, do której coś wysyłacie. To cudzy kod, który wpuszczacie do własnego pipeline'u.

1. Napastnik zdobywa prawo push do repo akcji: wykradziony token maintainera albo bota, przejęte konto, niedokończona rotacja kluczy po wcześniejszym incydencie.
2. Dodaje commit ze złośliwym kodem (nie musi być na żadnej gałęzi).
3. Przestawia na niego tagi — wszystkie albo prawie wszystkie (`v1`…`v45`).
4. Tysiące workflow na świecie przy najbliższym przebiegu pobierają nowy kod. **Nikt nic nie zmienił w swoim repo.**
5. Złośliwy kod działa w jobie: czyta zmienne środowiskowe i pamięć procesu runnera, pliki z poświadczeniami (`~/.aws`, `~/.kube`, `.git/config`), i wysyła je na zewnątrz.
6. Na koniec wykonuje to, co akcja normalnie robi (skan, lista plików). **Build jest zielony.**

### Co akcja ma w ręku

| Zasób | Skąd się bierze | Jak ograniczyć |
|---|---|---|
| `GITHUB_TOKEN` | GitHub daje go każdemu jobowi | `permissions:` minimalne, per job |
| Sekrety repo / organizacji | `${{ secrets.X }}` w `env:` lub `with:` | tylko te, których job potrzebuje |
| Poświadczenia chmury | klucze w sekretach albo token OIDC | OIDC: token żyje ok. godziny, rola ufa tylko wybranej gałęzi |
| Token w `.git/config` | `actions/checkout` z domyślnym `persist-credentials: true` | `persist-credentials: false` |
| Kod repo | checkout | — |

**Dlaczego to takie groźne:** to atak, w którym ofiara nic nie robi. Nie ma PR-a do review, nie ma zmiany w Waszym repo, nie ma czerwonego builda.

---

## 4. Case study

### 4.1 tj-actions/changed-files (marzec 2025, CVE-2025-30066)

- Popularna akcja (lista zmienionych plików w PR), ok. **23 000 repozytoriów**.
- 14–15.03.2025 napastnik użył wykradzionego tokenu (PAT) bota z dostępem do repo i **przestawił tagi od v1 do v45.0.7** na jeden złośliwy commit.
- Kod skanował pamięć procesu runnera i wypisywał znalezione sekrety (zakodowane base64) do logów joba. W repo publicznych logi są publiczne — sekrety mógł przeczytać każdy.
- Poszkodowani: wszyscy na tagach. **Bezpieczni: przypięci do SHA sprzed ataku.**
- W tym samym łańcuchu: `reviewdog/action-setup@v1` (CVE-2025-30154) — tak napastnik dostał się dalej.

### 4.2 aquasecurity/trivy-action (marzec 2026, CVE-2026-33634)

Szczegóły i lista wersji: [`docs/12-security-trivy-ghas/security-trivy-ghas.md`](../12-security-trivy-ghas/security-trivy-ghas.md), sekcja 4.1 (materiał z dnia 3).

- Trivy to skaner bezpieczeństwa — narzędzie, które miało **chronić** pipeline.
- Początek marca: wyciek poświadczeń projektu; **rotacja kluczy nie objęła wszystkich naraz**. Grupa TeamPCP wykorzystała pozostały dostęp.
- 19–20.03: **76 z 77 tagów `trivy-action`** i wszystkie tagi `setup-trivy` przestawione na złośliwy kod. Do tego złośliwa binarka i obrazy na Docker Hub.
- Kod najpierw kradł: pamięć runnera, klucze SSH, poświadczenia AWS/GCP/Azure, tokeny Kubernetes, konfigurację Dockera. Potem uruchamiał normalny skan → **zielony build**.
- Ta sama grupa uderzyła później w LiteLLM — bramę AI, której używamy na szkoleniu.
- **Bezpieczni: pipeline'y z `trivy-action` przypiętym do SHA.**

**Lekcja z obu:** narzędzie, które ma dostęp do sekretów CI, jest atrakcyjnym celem — im popularniejsze, tym bardziej. Tag oznacza, że bezpieczeństwo Waszego pipeline'u zależy od bezpieczeństwa cudzego konta.

---

## 5. Najlepsze praktyki

### 5.1 Przypinaj do pełnego SHA, z komentarzem wersji

```yaml
- uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
  with:
    persist-credentials: false
```

- **Pełne 40 znaków.** Skrócony SHA nie jest akceptowany przez GitHub Actions.
- **Komentarz `# v5.0.1`** jest dla ludzi i dla Dependabota/Renovate (po nim rozpoznają wersję).
- Dotyczy **wszystkich** akcji, także `actions/*` od GitHuba. Najważniejsze przy akcjach firm trzecich i małych projektów.

### 5.2 Skąd brać SHA

Nigdy z pamięci (swojej ani modelu). Ze źródła — trzy sposoby, wynik ten sam:

**1. Strona wydania (bez terminala)**
`github.com/actions/checkout` → **Releases** → wybierasz wersję (np. v5.0.1) → klikasz skrócony hash commita przy tagu → pełne 40 znaków jest w nagłówku commita i w adresie strony.

**2. `git ls-remote` (terminal, bez klonowania repo)**

```bash
git ls-remote https://github.com/actions/checkout 'refs/tags/v5.0.1*'
# 93cb6efe18208431cddfb8368fd83d5badbf9bfd  refs/tags/v5.0.1
```

Pytasz GitHuba wprost: „na jaki commit wskazuje ten tag?”.

- Jedna linia → to jest SHA commita.
- Dwie linie, w tym jedna z `^{}` na końcu (tag „annotated”) → bierz tę z `^{}`. Druga to hash obiektu tagu, nie commita. Przykład: `azure/setup-helm`.

**3. GitHub CLI (`gh`)**

```bash
gh api repos/actions/checkout/commits/v5.0.1 --jq .sha
# 93cb6efe18208431cddfb8368fd83d5badbf9bfd
```

`gh` od razu zwraca SHA commita — także dla tagów annotated, bez szukania linii z `^{}`.

**Potem wpisujesz:**

```yaml
- uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
```

**Na co dzień nikt tego nie robi ręcznie:**

- **pierwszy raz** — agent AI: *„Przypnij akcje do pełnego SHA. SHA sprawdź poleceniem git ls-remote, nie z pamięci”* (tak w demie prowadzącego i w lab03),
- **potem** — Dependabot robi PR z nowym SHA (sekcja 5.3), Wy mergujecie,
- **kontrola** — zizmor zgłasza każdą akcję bez SHA (sekcja 5.6).

### 5.3 Aktualizacje: Dependabot albo Renovate

SHA się nie aktualizuje sam — i o to chodzi. Aktualizacje przychodzą jako PR, który ktoś czyta:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

Dependabot rozumie format `@<sha>  # vX.Y.Z` i robi PR z nowym SHA, nowym komentarzem i changelogiem.

### 5.4 Skąd wiemy, że SHA jest dobry i aktualny

**SHA nie gwarantuje, że kod jest dobry. Gwarantuje tylko, że się nie zmieni.** Ocenę „dobry” robicie raz — w chwili wyboru. SHA sprawia, że ta ocena obowiązuje dalej, bo nikt nie podmieni kodu pod spodem.

**Że jest dobry — w chwili wyboru:**

- SHA z **oficjalnego wydania** (zakładka *Releases* albo `git ls-remote` na tagu wersji, sekcja 5.2) — nie z linku od kogoś i nie z odpowiedzi AI.
- **Nie przypinajcie wersji wydanej przed chwilą.** Oba ataki z sekcji 4 trwały od kilku godzin do kilku dni i zostały wykryte. Kto pobrał SHA w tym oknie, przypiął zły kod — i będzie go uruchamiał, dopóki ktoś nie zauważy.
- Przy ważnych akcjach (dostęp do chmury, sekretów, publikacji) rzut oka na changelog: co się zmieniło.

**Że jest aktualny — z czasem:**

- **Dependabot** robi PR z nowym SHA, gdy wyjdzie nowa wersja. Z opcją **`cooldown`** — dopiero gdy wydanie jest dostępne od N dni. Od 14.07.2026 domyślny cooldown dla aktualizacji wersji to 3 dni; można go wydłużyć:
  ```yaml
  # .github/dependabot.yml
  version: 2
  updates:
    - package-ecosystem: github-actions
      directory: /
      schedule:
        interval: weekly
      cooldown:
        default-days: 7
  ```
- **Alerty bezpieczeństwa:** baza podatności GitHuba obejmuje też akcje. Jeśli przypięty SHA ma znaną dziurę, Dependabot zgłosi alert, a **aktualizacje bezpieczeństwa nie czekają na cooldown**. Podobny audyt w zizmor: `known-vulnerable-actions`.

**Zmiana myślenia:**

| Tag | SHA |
|---|---|
| Aktualizacje wchodzą **same i po cichu** — dobre i złe | Aktualizacje wchodzą **przez PR**, który ktoś widzi |
| Ufacie cudzemu kontu w każdej chwili | Ufacie wersji, którą świadomie wybraliście |
| Nowe wydanie działa u Was od razu | Nowe wydanie czeka kilka dni, aż świat je sprawdzi |

**Jednym zdaniem:** *„SHA nie mówi, że kod jest dobry. Mówi, że to ten sam kod, który sprawdziliście. Nowe wersje przychodzą jako PR od Dependabota z kilkudniowym opóźnieniem, a nie po cichu w środku nocy.”*

### 5.5 Ogranicz, co akcja może ukraść

Przypięcie chroni przed podmianą. Ograniczenia zmniejszają szkody, gdy coś jednak pójdzie źle (np. przypiąłeś SHA, który już był złośliwy):

- `permissions:` minimalne, ustawiane **per job** (na poziomie workflow `permissions: {}`).
- **OIDC zamiast kluczy** do chmury — krótkie tokeny, rola ufa tylko konkretnej gałęzi.
- Sekrety tylko w jobach, które ich potrzebują.
- `persist-credentials: false` przy checkout.

### 5.6 Sprawdzaj narzędziem

- **zizmor** — audyt bezpieczeństwa workflow. `unpinned-uses` zgłasza akcje bez SHA (domyślnie jako `high`), do tego `excessive-permissions`, `artipacked`, `template-injection`, `impostor-commit`.
- **actionlint** — składnia i typowe błędy; nie sprawdza pinowania.
- Szybki przegląd ręczny:
  ```bash
  grep -rn 'uses:' .github/workflows | grep -v '@[0-9a-f]\{40\}'
  ```

### 5.7 Wymuś na poziomie organizacji

- **Polityka „allowed actions”** (od 08.2025): opcja wymagająca przypięcia do pełnego SHA. Workflow z akcją na tagu po prostu się nie uruchomi. Do ustawienia na poziomie enterprise, organizacji lub repo.
- **Lista dozwolonych akcji** (np. tylko `actions/*`, `aws-actions/*` i wskazane repo) — mniej obcego kodu w ogóle.
- **Immutable releases** (GA 10.2025) — po stronie **autora** akcji: tagi nowych wydań są zablokowane, nie da się ich przestawić ani usunąć. Jeśli wydajecie własne akcje, włączcie to.

---

## 6. Czego SHA nie załatwia

- **Przypięcie złego SHA** — jeśli przypniesz commit, który już jest złośliwy, będziesz go uruchamiać na zawsze. Dlatego SHA ze źródła, a aktualizacje przez PR z changelogiem.
- **Zależności przechodnie** — akcja przypięta do SHA może w środku pobierać coś „na żywo”: obraz `:latest`, binarkę z „najnowszego wydania”, inną akcję po tagu. W trivy-action złośliwa była też sama binarka i obrazy Dockera.
- **Impostor commit** — SHA z forka repo akcji da się czasem wywołać przez nazwę oryginału (GitHub dzieli obiekty w sieci forków). Dlatego SHA bierzesz z tagu/wydania oryginału, nie z linku od kogoś. zizmor ma na to audyt `impostor-commit`.
- **Stare wersje** — SHA jest prawdziwy, ale wersja sprzed kilku wydań, bez poprawek bezpieczeństwa. Bez Dependabota przypięcie „zamraża” też dziury.
- **Reusable workflows** (`uses: org/repo/.github/workflows/x.yml@ref`) — to samo ryzyko, przypinaj tak samo.

---

## 7. Gdzie w tym jest AI

- **Model pisze tagi.** Poproszony o workflow pisze to, co widział najczęściej: `actions/checkout@v4`, często starą wersję. W demie prowadzącego zizmor zgłasza 10× `unpinned-uses`.
- **Model zmyśla SHA.** Poproszony o przypięcie poda 40 znaków. Trzy możliwości:
  1. prawdziwy i zgodny z wersją — OK;
  2. zmyślony — przebieg pada z „unable to resolve action” (dobry scenariusz, błąd widać od razu);
  3. prawdziwy, ale z innej wersji niż komentarz obok — działa, recenzent ufa komentarzowi, a uruchamiacie starą wersję (zły scenariusz, cichy).
- **Jak to robić z AI:** w prompcie wymaganie zamiast nazw akcji („akcje przypięte do pełnego SHA, SHA sprawdź git ls-remote”), potem zizmor. Agent z dostępem do terminala sam wywoła `git ls-remote` — w demie robi to po zgodzie.
- **Zasada szkolenia w jednym zdaniu:** *AI pisze, narzędzie sprawdza, SHA bierzesz ze źródła.*

---

## 8. Pytania uczestników i odpowiedzi

**„Przecież `actions/checkout` jest od GitHuba. Też mam przypinać?”**
Ryzyko jest mniejsze, ale konto i proces GitHuba też da się zaatakować, a polityka organizacji wymaga SHA dla wszystkich. Prościej mieć jedną zasadę bez wyjątków.

**„To jak dostanę poprawki bezpieczeństwa, skoro wersja jest zamrożona?”**
Dependabot (`package-ecosystem: github-actions`) robi PR z nowym SHA i changelogiem. Aktualizacja jest świadoma — przechodzi przez review, zamiast wejść po cichu.

**„Czy `@v4.2.0` nie wystarczy? Przecież wersji konkretnej nikt nie przestawia.”**
Uczciwy maintainer nie przestawia. Napastnik w obu case study przestawił właśnie tagi konkretnych wersji — w tj-actions od v1 do v45.0.7. Przed napastnikiem chroni tylko SHA (albo immutable release po stronie autora).

**„Skąd wiem, że SHA, który przypinam, jest dobry?”**
Nie wiesz tego z samego SHA — SHA gwarantuje niezmienność, nie jakość. Bierzesz go z oficjalnego wydania, które ma już kilka dni (cooldown), a później pilnuje Dependabot i alerty bezpieczeństwa. Szczegóły: sekcja 5.4.

**„SHA to SHA-1. A kolizje?”**
Praktyczny atak wymaga ogromnych zasobów, a GitHub wykrywa znane techniki kolizji SHA-1. Realne ryzyko to przestawiony tag, nie kolizja.

**„Skąd mam wiedzieć, który SHA jest teraz używany, jeśli mam tagi?”**
Log joba → *Set up job* → linia `Download action repository '…@v4' (SHA:…)`. Dobre do śledztwa po incydencie: widać, jaki kod naprawdę się wykonał.

**„Co zrobić, jeśli korzystałem z tj-actions albo trivy-action w oknie ataku?”**
Przejrzeć logi przebiegów z tych dni, **zrotować wszystkie sekrety** dostępne dla tych jobów (rotacja pełna i naraz — niedokończona rotacja umożliwiła atak na Trivy), szukać w organizacji obcych repo (`tpcp-docs`).

**„Czy to dotyczy Azure DevOps / GitLab CI?”**
Ten sam problem w innej formie: zadania z marketplace (Azure DevOps), `include:` z innych repo i obrazy `:latest` (GitLab). Zasada ta sama: przypnij do niezmiennego identyfikatora (commit, digest obrazu `@sha256:…`).

---

## 9. Ściąga komend

```bash
# SHA dla tagu (linia z ^{} = commit przy tagu annotated)
git ls-remote https://github.com/<owner>/<akcja> 'refs/tags/<wersja>*'

# akcje bez SHA w moich workflow
grep -rn 'uses:' .github/workflows | grep -v '@[0-9a-f]\{40\}'

# audyt bezpieczeństwa workflow
zizmor .github/workflows/

# składnia workflow
actionlint
```

Wzorzec kroku:

```yaml
permissions: {}                      # workflow: nic domyślnie

jobs:
  test:
    permissions:
      contents: read                 # job: tylko to, czego potrzebuje
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
        with:
          persist-credentials: false
```

---

## Źródła

- GitHub Docs — Secure use reference (pinowanie akcji): https://docs.github.com/en/actions/reference/security/secure-use
- GitHub Changelog, 15.08.2025 — polityka blokowania i wymuszania SHA: https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/
- Dependabot — domyślny cooldown 3 dni od 14.07.2026 (omówienie): https://dev.classmethod.jp/en/articles/dependabot-default-cooldown-3-days/
- GitHub Changelog, 28.10.2025 — immutable releases GA: https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/
- GitHub Docs — immutable releases: https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- CISA — tj-actions/changed-files (CVE-2025-30066) i reviewdog (CVE-2025-30154): https://www.cisa.gov/news-events/alerts/2025/03/18/supply-chain-compromise-third-party-tj-actionschanged-files-cve-2025-30066-and-reviewdogaction
- Wiz — analiza ataku na tj-actions: https://www.wiz.io/blog/github-action-tj-actions-changed-files-supply-chain-attack-cve-2025-30066
- Trivy — CVE-2026-33634: źródła w [`../12-security-trivy-ghas/security-trivy-ghas.md`](../12-security-trivy-ghas/security-trivy-ghas.md)
- zizmor — audyty: https://docs.zizmor.sh/audits/
