# lab03 — Pipeline z AI: Twoja Kantyna z forka na Twój namespace

**Zasada:** pipeline jest gotowy, gdy przechodzi `actionlint` i `zizmor`, a nowa wersja działa w klastrze. Nie wtedy, gdy AI powie, że jest gotowy.

**Po labie masz:** workflow GitHub Actions wygenerowany z opisu słownego, który testuje i buduje Kantynę i wdraża ją na Twój namespace. Bez ani jednego klucza w GitHubie.

## Zanim zaczniesz

- zdrowa Kantyna w Twoim namespace (`setup/check.sh` → `SUKCES: 11/11`)
- `gh` zalogowane (`gh auth login`), `actionlint`, `zizmor` (albo `uvx zizmor`), Claude Code i `kubectl` z dnia 1
- od prowadzącego dwie wartości: `AWS_ROLE_ARN` i `ECR_REGISTRY` (to nie są sekrety); `K8S_NAMESPACE` to Twój login

## 1. Przygotuj fork

`gh repo set-default` wskazuje Twój fork. Bez tego `gh` może zapisać zmienne w repo prowadzącego (`upstream`).

```bash
git pull upstream main
gh repo set-default <Twój GitHub>/aiops-praktyka
gh variable set AWS_ROLE_ARN --body <wartość od prowadzącego>
gh variable set ECR_REGISTRY --body <wartość od prowadzącego>
gh variable set K8S_NAMESPACE --body <login>
```

W forku na GitHubie otwórz zakładkę **Actions** i kliknij „I understand my workflows, go ahead and enable them”.

✅ `gh variable list` pokazuje trzy zmienne, a Actions w forku są włączone.

## 2. Wygeneruj pipeline z opisu

Claude Code w trybie planu (`Shift+Tab`). Wklej opis:

```text
Pipeline CI/CD dla app/ w tym repo (GitHub Actions, .github/workflows/ci.yml).
Wyzwalacze: push na main (wdrożenie) i pull_request (tylko testy),
zmiany w app/** albo w .github/workflows/ci.yml.
Etapy: testy orders-api (uv, Python 3.12) i payments (go test) →
build 4 obrazów: orders-api, payments, worker, web (Postgresa i loadgena NIE budujemy) →
push do ECR: ${ECR_REGISTRY}/kantyna/<serwis>:<SHA commita> →
helm upgrade kantyna app/deploy/helm/kantyna w namespace ${K8S_NAMESPACE}
z --reuse-values i --set global.imageRegistry/global.imageTag → kubectl rollout status
→ smoke test /healthz z wnętrza klastra.
AWS: OIDC (rola ${AWS_ROLE_ARN}), żadnych kluczy; region eu-central-1, klaster aiops.
Ograniczenia: akcje przypięte do pełnego SHA z komentarzem wersji, permissions
minimalne per job, cache, timeout-minutes. Zmienne z vars, nie z secrets.
Helm w wersji v4.3.0 przypięty w workflow (nie ten z obrazu runnera).
Akceptacja: actionlint i zizmor bez błędów, zielony przebieg, nowe obrazy w namespace.
Najpierw przeczytaj Makefile, Dockerfile'e, go.mod i chart; wypisz komendy.
```

Przeczytaj plan: czy komendy testów i buildu zgadzają się z `Makefile` i Dockerfile'ami? Dopiero potem zgódź się na zapis `.github/workflows/ci.yml`.

✅ Plik `.github/workflows/ci.yml` istnieje.

## 3. Sprawdź workflow narzędziami

`actionlint` sprawdza składnię i typowe błędy workflow, a `zizmor` problemy bezpieczeństwa.

```bash
actionlint
zizmor .github/workflows/ci.yml
```

Błędy wklejaj agentowi jako kontekst do poprawki. Sprawdzaj też według checklisty niżej.

Agent lubi wymyślać SHA akcji. Każdy sprawdź sam:

```bash
git ls-remote https://github.com/<owner>/<akcja> 'refs/tags/<wersja>*'
```

Dwie linie w wyniku? SHA commita to ta z `^{}` na końcu.

✅ Oba narzędzia nie zgłaszają błędów, a każdy SHA zgadza się z `git ls-remote`.

## 4. Puść pipeline i doprowadź go do zielonego

```bash
git add .github/workflows/ci.yml
git commit -m "ci: pipeline Kantyny"
git push
```

Przebieg zobaczysz w zakładce **Actions** albo przez `gh run list`. Gdy jest czerwony:

1. Pobierz błąd: `gh run view <id> --log-failed | tail -100`.
2. Zdiagnozuj go z agentem (szablon `docs/prompts/diagnoza.md`).
3. Zrób jedną poprawkę i wypchnij ją (`git push`).
4. Dopisz wiersz do dziennika.

✅ Ostatni przebieg na `main` jest zielony.

## 5. Sprawdź, co działa w klastrze

```bash
kubectl get deploy -n <login> \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
setup/check.sh
```

✅ orders-api, payments, worker i web działają na obrazach `<ECR_REGISTRY>/kantyna/<serwis>:<SHA Twojego commita>`, a `check.sh` pokazuje 11/11.

## 6. Podsumuj

Dopisz w dzienniku jedną sugestię AI, której nie wdrożyłeś, i dlaczego.

## Checklista

- [ ] każda akcja przypięta do pełnego SHA z komentarzem wersji; SHA sprawdzony `git ls-remote`
- [ ] `permissions: contents: read` na poziomie workflow; więcej tylko w jobie, który tego potrzebuje
- [ ] AWS przez OIDC (rola z `vars.AWS_ROLE_ARN`), zero kluczy w repo i w secrets
- [ ] cache zależności i warstw Dockera
- [ ] `timeout-minutes` w każdym jobie, `concurrency` dla gałęzi
- [ ] aktualne wersje akcji, runnera, Pythona i Go

## Dziennik

Skopiuj tabelę do pliku `lab03/dziennik.md` w swoim forku.

| # | Objaw (krok, komunikat) | Hipoteza (AI / ja) | Jak sprawdziłem | Poprawka | Status |
|---|---|---|---|---|---|
| 1 | | | | | ✅/❌ |

## SUKCES

- [ ] ostatni przebieg workflow w Twoim forku jest zielony, a `actionlint` i `zizmor` nie zgłaszają błędów
- [ ] checklista spełniona w całości
- [ ] 4 deploymenty Kantyny działają na obrazach z Twojego commita
- [ ] `setup/check.sh` → `SUKCES: 11/11`
- [ ] w dzienniku jest co najmniej jedna sugestia AI, której nie wdrożyłeś, z uzasadnieniem

## Dla chętnych

- Zmień coś widocznego (np. tekst w `app/web/html`), zrób commit na `main` i po przebiegu zobacz swoją wersję na `https://<login>.aiops.marniok.dev`.
- Dodaj Dependabota dla `github-actions` (`.github/dependabot.yml`). Kto teraz aktualizuje SHA akcji?
- Poproś agenta o wersję Twojego workflow dla Azure Pipelines i porównaj z oryginałem.

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Po pushu nie ma przebiegu | Actions w forku nie są włączone albo filtr ścieżek nie pasuje do zmienionych plików |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | Przebieg nie jest z `main` albo prowadzący ma inny adres Twojego forka. Podaj mu dokładny adres |
| `denied` przy pushu do ECR | Sprawdź, do jakiego repozytorium pushujesz (`ECR_REGISTRY`) |
| `Kubernetes cluster unreachable` / `Unauthorized` przy `helm` | Przed `helm` w workflow musi być `aws eks update-kubeconfig --name aiops --region eu-central-1` |
| `ImagePullBackOff` po wdrożeniu | `kubectl describe pod` i porównaj nazwę obrazu z tym, co wypchnął pipeline |
| `check.sh` spadł mimo zielonego przebiegu | `helm get values kantyna -n <login>` i zgłoś prowadzącemu |
| `gh: To get started with GitHub CLI…` | `gh auth login` |
| Błąd limitu zapytań w Claude Code | Krótszy log (`… --log-failed \| tail -100`), `/clear` między krokami |
