# lab06b — Trivy i AI: od listy podatności do kolejki napraw

**Zasada:** skaner mówi, co jest w plikach. AI ustala tylko kolejność. Każde ID i każdą wersję z odpowiedzi AI sprawdzasz w wyniku skanera.

**Po labie masz:** listę trzech podatności do naprawy w Twojej Kantynie z uzasadnieniem. Każda jest sprawdzona w wyniku Trivy. Wiesz też, które znaleziska w chartcie to szum i czego skan kodu nie widzi.

## Zanim zaczniesz

- `trivy` z lab04. Sprawdź wersję, bo 0.69.4–0.69.6 to wersje z incydentu łańcucha dostaw:

```bash
trivy --version
```

- terminal w katalogu swojego forka, Claude Code uruchamiane z tego samego katalogu
- katalog na wyniki:

```bash
mkdir -p lab06b
```

✅ `trivy --version` pokazuje inną wersję niż 0.69.4, 0.69.5 i 0.69.6.

## 1. Skan zależności aplikacji

Trivy czyta pliki zależności (`requirements.txt`, `uv.lock`, `go.mod`) w kodzie Kantyny i porównuje wersje z bazą podatności. Nie potrzebuje obrazu ani logowania do ECR.

Najpierw wszystko, bez filtra:

```bash
trivy fs --scanners vuln app/
```

Przy pierwszym uruchomieniu Trivy pobiera bazę podatności, co trwa do minuty.

Teraz tylko to, co jest groźne i ma gotową poprawkę:

```bash
trivy fs --quiet --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --table-mode detailed app/
```

Zapisz w `lab06b/notatki.md`:
- ile podatności jest bez filtra, a ile po filtrze,
- w których plikach je znaleziono,
- `orders-api` ma dwa pliki zależności: `requirements.txt` i `uv.lock`. W którym są znaleziska i dlaczego nie w obu? Otwórz oba pliki i poszukaj pakietu `starlette`.

✅ Znasz liczbę podatności przed filtrem i po nim. Wiesz, z którego pliku pochodzą.

## 2. Skan charta: co jest problemem, a co szumem

```bash
trivy config --quiet app/deploy/helm/kantyna
```

Każde znalezisko ma ID (np. `KSV032`), tytuł i ważność. Przejrzyj je i zdecyduj sam, zanim zapytasz AI: które z nich dotyczą Kantyny na EKS w AWS, a które nie mają tu sensu?

Potem nowa sesja `claude`:

```text
Uruchom: trivy config --quiet app/deploy/helm/kantyna
Kontekst: Kantyna działa na EKS w AWS, obrazy są w ECR, każdy zespół ma własny namespace.
Podziel znaleziska na trzy grupy: do naprawy, do świadomej akceptacji, szum (reguła nie pasuje
do tego środowiska). Dla każdego podaj ID i jedno zdanie uzasadnienia. Nie zmieniaj żadnych plików.
```

Porównaj podział AI ze swoim. Zapisz w `lab06b/notatki.md` jedno znalezisko, przy którym się różnicie.

✅ Każde znalezisko z charta ma u Ciebie przypisaną grupę i wiesz, które reguły to szum.

## 3. AI układa kolejkę napraw

Zapisz wynik skanu jako JSON. Ten plik jest źródłem prawdy dla AI i dla Ciebie:

```bash
trivy fs --quiet --scanners vuln --format json app/ > lab06b/wynik.json
```

Plik zawiera wszystkie podatności, bez filtra. W tej samej sesji `claude`:

```text
Przeczytaj lab06b/wynik.json (wynik Trivy dla kodu aplikacji Kantyna).
Kontekst: orders-api to API w Pythonie (FastAPI) wystawione do internetu przez ALB,
bez uwierzytelnienia użytkowników, dane zamówień w Postgresie. Payments to wewnętrzny serwis w Go.
Wybierz 3 podatności do naprawy najpierw. Dla każdej: ID, pakiet, wersja zainstalowana,
wersja z poprawką i jedno zdanie, dlaczego właśnie ta. Korzystaj tylko z danych z pliku.
Nie podawaj ID ani wersji, których nie ma w pliku. Zapisz odpowiedź do lab06b/kolejka.md.
```

✅ `lab06b/kolejka.md` zawiera trzy podatności z ID, wersjami i uzasadnieniem.

## 4. Sprawdź AI w wyniku skanera

Dla każdej z trzech podatności z `lab06b/kolejka.md` sprawdź ID i wersje w pliku. Wstaw ID zamiast `CVE-…`:

```bash
jq -r '.Results[] | .Target as $plik | .Vulnerabilities[]?
  | select(.VulnerabilityID=="CVE-…")
  | "\($plik): \(.PkgName) \(.InstalledVersion) → \(.FixedVersion) (\(.Severity))"' lab06b/wynik.json
```

Pusty wynik oznacza, że takiego ID nie ma w pliku. Wtedy AI je wymyśliło albo wzięło z pamięci.

Na koniec odpowiedz w `lab06b/notatki.md`:
- Czy wszystkie ID i wersje z odpowiedzi AI zgadzają się z plikiem?
- Czy AI wybrało coś o niższej ważności zamiast HIGH? Czy uzasadnienie to obroni?
- Ten skan widzi tylko pliki z kodu. Czego nie widzi, co jest w obrazie, który działa na klastrze?

✅ Każde ID w `lab06b/kolejka.md` ma dopasowanie w `lab06b/wynik.json` albo jest oznaczone jako wymyślone.

## SUKCES

- [ ] `lab06b/notatki.md`: liczby z kroku 1, plik ze znaleziskami i odpowiedź, dlaczego tylko w jednym pliku
- [ ] znaleziska z charta podzielone na grupy, co najmniej jedna reguła oznaczona jako szum
- [ ] `lab06b/kolejka.md`: trzy podatności, każda sprawdzona komendą `jq` w `lab06b/wynik.json`
- [ ] odpowiedź na pytanie, czego skan kodu nie widzi w obrazie

## Dla chętnych

- Zrób SBOM aplikacji i policz składniki: `trivy fs --quiet --format cyclonedx --output lab06b/sbom.json app/` i `jq '.components | length' lab06b/sbom.json`. Gdy wyjdzie nowe CVE, sprawdzisz je bez ponownego skanu kodu: `trivy sbom lab06b/sbom.json`.
- Uruchom krok 3 bez akapitu „Kontekst” i porównaj kolejkę. Czy kontekst usługi zmienił kolejność?
- Poproś AI o poprawkę pierwszej podatności z kolejki na **osobnej gałęzi** (nie na `main`, bo tę gałąź wdraża Twój pipeline). Potem uruchom skan jeszcze raz i sprawdź, czy podatność zniknęła.

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| `trivy: command not found` | instalacja z `setup/README.md` (sekcja narzędzi do lab04) |
| Pobieranie bazy kończy się błędem `TOOMANYREQUESTS` albo timeoutem | `trivy fs --db-repository public.ecr.aws/aquasecurity/trivy-db --scanners vuln app/` |
| `no such file or directory: app/` | jesteś poza katalogiem forka, `cd` do katalogu repo |
| `jq: command not found` | macOS: `brew install jq`, Ubuntu/WSL: `sudo apt install jq` |
| `budget exceeded` w Claude Code | zgłoś prowadzącemu |
