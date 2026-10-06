# Walidacja, testy i polityki IaC — co do czego służy

Materiał pomocniczy do szkolenia „AIOps w praktyce” (dzień 2: bramki z 2.3.2, testy i polityki z 2.4). Zbiera w jednym miejscu narzędzia do Terraform i polityki dla Kubernetesa, które pojawiają się na slajdach, w demach i w labach, żeby nie pomylić, które pytanie zadaje które narzędzie.

> Stan na 6 października 2026. Wersje jak w demach: Terraform 1.16, provider AWS 6.x. Trivy: **nie** v0.69.4 / v0.69.5 / v0.69.6 (atak na łańcuch dostaw, marzec 2026 — `docs/12-security-trivy-ghas/`).

---

## 1. Mapa: jedno narzędzie = jedno pytanie

| Narzędzie | Na jakie pytanie odpowiada | Łapie | Nie łapie | Chmura? | Czas |
|---|---|---|---|---|---|
| `terraform fmt -check` | Czy kod jest sformatowany? | wcięcia, wyrównanie | nic poza wyglądem | nie | ms |
| `terraform validate` | Czy konfiguracja pasuje do schematu providera? | wymyślone argumenty i bloki, złe typy, brak wymaganych pól, cykle | bezpieczeństwo, sens, czy AWS to przyjmie | nie (po `init -backend=false`) | s |
| `tflint` (+ `tflint-ruleset-aws`) | Czy kod nie ma błędów, które schemat przepuszcza? | nieistniejący typ instancji, przestarzała składnia, nieużywane zmienne, konwencje nazw | bezpieczeństwo (to nie jego rola) | nie | s |
| `trivy config` | Czy konfiguracja nie jest groźna wg znanych reguł? | `0.0.0.0/0`, brak szyfrowania, publiczny S3, IAM `*` (reguły `AVD-AWS-…`) | Wasze wymagania, replace zasobów | nie | s |
| `checkov` | to samo co Trivy, inny zestaw reguł | j.w. + reguły grafowe (powiązania między zasobami) | j.w. | nie | s |
| `terraform plan` | Co **naprawdę** się zmieni? | replace/destroy, dryf, błędy API, wartości z data source | czy zmiana ma sens | **tak** (poświadczenia + stan) | s–min |
| `terraform test` + `mock_provider` | Czy moduł spełnia nasze wymagania? (bez chmury) | logika modułu: wartości, warunki, liczba zasobów, polityki IAM | czy AWS przyjmie konfigurację | nie | s |
| `terraform test` z `command = apply` | j.w., na prawdziwych zasobach | j.w. + odrzucenia przez AWS | — | **tak**, tworzy i niszczy zasoby | min, koszt |
| `validation` / `precondition` / `postcondition` / `check` | Czy wejście i wynik spełniają warunki? (w samym kodzie modułu) | zła wartość zmiennej, złe założenie o data source | wszystko, czego autor nie przewidział | przy `plan`/`apply` | — |
| Conftest (OPA, Rego) na `terraform show -json` | Czy **każda** zmiana spełnia reguły organizacji? | „żaden SG z `0.0.0.0/0` na 22”, wymagane tagi, dozwolone regiony | — | potrzebuje planu | s |
| Terratest (Go) | Czy po wdrożeniu to działa? | endpoint odpowiada, limity konta, IAM odrzucone przez AWS | — | **tak** | min, koszt |
| Sentinel / OPA w HCP Terraform | jak Conftest, wbudowane w HCP Terraform | j.w. | — | HCP Terraform (płatne plany) | s |

**Dwie pary, które się myli:**
- **`validate` vs `tflint`**: `validate` zna tylko schemat providera („czy pole `instance_type` istnieje”). `tflint` z rulesetem AWS wie, że `t3.mega` nie istnieje, choć to poprawny string.
- **`trivy config` vs `checkov`**: robią to samo (skan konfiguracji), mają różne zestawy reguł. Wystarczy jeden; na szkoleniu używamy Trivy (ten sam skaner w 3.4 do obrazów i sekretów). `tfsec` został wchłonięty przez Trivy.

---

## 2. Trzy poziomy testów (slajd 2.4.1)

| Poziom | Na czym | Czym | Koszt |
|---|---|---|---|
| **statyczny** | kod, plan | `terraform test` z `command = plan` lub mockiem | sekundy, bez chmury |
| **polityka** | plan w JSON | Conftest / OPA, Sentinel | sekundy |
| **zachowanie** | wdrożone zasoby | `terraform test` z `apply`, Terratest, smoke test | minuty, prawdziwe zasoby i pieniądze |

Im dalej w prawo, tym drożej i wolniej — więc większość testów po lewej, po prawej kilka smoke testów.

---

## 3. Gdzie co uruchamiać (slajd 2.4.5)

| Moment | Bramki |
|---|---|
| pre-commit / lokalnie | `terraform fmt -check`, `terraform validate`, `tflint`, `terraform test` (mock) |
| PR | `trivy config`, `terraform plan` (rola read-only przez OIDC), Conftest na planie, review AI (2.1) + człowiek |
| merge / nocny pipeline | `terraform test` z `apply`, Terratest — osobne konto AWS, budżet |
| po wdrożeniu | smoke test; czerwony = rollback |

---

## 4. Komendy

```bash
# 1. Format i schemat (offline)
terraform fmt -check -recursive
terraform init -backend=false        # pobiera providera, bez stanu
terraform validate

# 2. Lint
tflint --init                        # pobiera ruleset z .tflint.hcl
tflint --recursive

# 3. Skan konfiguracji (offline)
trivy config --severity HIGH,CRITICAL .
checkov -d .                         # alternatywa

# 4. Plan (chmura) i plan jako dane dla polityk/skanerów
terraform plan -out tfplan
terraform show -json tfplan > tfplan.json
conftest test tfplan.json            # polityki Rego z katalogu policy/
trivy config tfplan.json             # skan planu zamiast kodu

# 5. Testy
terraform test                       # wszystkie tests/*.tftest.hcl
terraform test -filter=tests/iam.tftest.hcl
```

Minimalny test z mockiem (wzór z `d2-t4-01`):

```hcl
# tests/s3.tftest.hcl
mock_provider "aws" {
  source = "./tests/mocks"           # wspólne *.tfmock.hcl zespołu
}

run "bucket_nie_jest_publiczny" {
  command = plan
  assert {
    condition     = aws_s3_bucket_public_access_block.receipts.block_public_acls == true
    error_message = "Bucket na paragony musi blokować publiczne ACL"
  }
}
```

---

## 5. Jak ocenić test od AI: mutacja

`terraform test` od AI prawie zawsze jest zielony. To nic nie mówi. Ocena trwa minutę:

1. Zepsuj w module jedną linię, którą test ma chronić (`block_public_acls = false`, `sqs:*` na `*`, usunięta `redrive_policy`).
2. `terraform test` → musi być **czerwony** z czytelnym `error_message`.
3. Cofnij zmianę → musi być **zielony**.

| Prompt | Wynik próby 4.10 (`d2-t4-01`, sonnet) |
|---|---|
| „Napisz testy `terraform test` do tego modułu” | 6–11 testów, zielone; po `sqs:*` na `*` **dalej zielone** (4 z 4 prób) — AI przepisało literalne wartości z `main.tf`, polityk IAM z nieznanym ARN nie testowało |
| „Wymagania: … Jedno wymaganie = jeden `run`. Każda asercja musi się wywalić, gdy wymaganie zostanie złamane.” | 3 testy; po mutacji **1 czerwony** („Każdy statement roli orders-api musi dotyczyć wyłącznie ARN kolejki orders”) |

Pułapki `terraform test`:
- `command = plan`: wartości znane dopiero po utworzeniu (ARN, JSON polityki z ARN) są nieznane → „Unknown condition value”. Dla IAM `command = apply` na mocku.
- Pusty `mock_provider "aws" {}` generuje losowe napisy, które provider odrzuca (JSON polityki, ARN roli) → wspólny plik `tests/mocks/*.tfmock.hcl` z `mock_data` / `mock_resource`.
- `expect_failures` — test, który **ma** się wywalić (np. zła wartość zmiennej z `validation`). Dobre do sprawdzania walidacji wejścia.
- Test wygenerowany z kodu powtarza błąd z kodu. Prompt zaczyna się od listy wymagań, nie od „napisz testy”.

---

## 6. Polityki: Conftest, Kyverno, ValidatingAdmissionPolicy

| | Conftest (OPA, Rego) | Kyverno | ValidatingAdmissionPolicy (VAP) |
|---|---|---|---|
| Czego pilnuje | **dowolny plik strukturalny**: plan Terraform w JSON, YAML, Dockerfile | zasoby **Kubernetes** | zasoby **Kubernetes** |
| Język | Rego | YAML (`ClusterPolicy`) lub CEL (`ValidatingPolicy` od 1.19) | CEL |
| Gdzie działa | pipeline / lokalnie | w klastrze (admission) **i** offline (CLI) | tylko w klastrze, wbudowane w Kubernetes (GA od 1.30) |
| Komendy | `conftest test tfplan.json` · `conftest verify` (testy samych reguł) | `kyverno apply polityka.yaml --resource plik.yaml` · `kyverno test .` | `kubectl apply -f vap.yaml` + `ValidatingAdmissionPolicyBinding` |
| Kiedy wybrać | polityki dla Terraform w CI | polityki K8s z CLI, testami, mutacją i raportami | proste reguły K8s bez dodatkowego narzędzia |

Inne, rzadziej spotykane: **Sentinel** (HCP Terraform / Enterprise, płatne plany), **OPA Gatekeeper** (OPA jako admission controller w Kubernetes).

**Polityka od AI — trzy pułapki (próby 4.10, `d2-t4-02`, Kyverno CLI 1.19.1):**
1. **Format sprzed roku.** 2 z 3 prób dały `kyverno.io/v1 ClusterPolicy` — od Kyverno 1.19 przestarzałe (CLI ostrzega), zastępuje je `policies.kyverno.io/v1 ValidatingPolicy` z CEL. W prompcie podawaj wersję narzędzia.
2. **Kotwica `=()`** znaczy „sprawdź, **tylko jeśli** pole istnieje”. Reguła `=(securityContext): =(runAsNonRoot): true` przepuszcza kontener **bez** `securityContext` — czyli dokładnie ten, który miała zatrzymać. Wynik na złym Deploymencie: wersja z dziurą `pass: 1, fail: 1`, poprawna `fail: 2`.
3. **Audit zamiast Enforce** w klastrze tylko raportuje. Offline `kyverno apply` pokazuje `fail` w obu trybach — nie daj się zmylić.

Zasada jak przy testach: do każdej polityki **dwa pliki — dobry i zły** — i `kyverno test` / `conftest verify` w pipeline. Polityka, której nikt nie widział czerwonej, niczego nie blokuje.

```bash
# Kyverno offline na wyrenderowanym chartcie
helm template kantyna app/deploy/helm/kantyna > rendered.yaml
kyverno apply polityka.yaml --resource zly.yaml        # musi być fail
kyverno apply polityka.yaml --resource rendered.yaml   # prawdziwy chart

# Conftest na planie Terraform
terraform show -json tfplan > tfplan.json
conftest test tfplan.json -p policy/
```

---

## 7. Gdzie AI pomaga, a gdzie się myli

| Narzędzie | AI dobrze | AI typowo źle |
|---|---|---|
| kod `.tf` | szkielet, typowe zasoby | styl z providera 3.x (bloki w `aws_s3_bucket`), wymyślone argumenty → łapie `validate` |
| `terraform test` | szkielet `run` / `assert` | składnia mocków (`mock_data` w złym miejscu), asercje na wartościach nieznanych w `plan` („Unknown condition value”); testuje to, co jest w kodzie, a nie wymagania |
| Kyverno | szkielet polityki, typowe reguły (root, `:latest`, limity) | przestarzały `ClusterPolicy`, kotwica `=()` przepuszczająca brak pola, dopasowanie tylko do `Pod` |
| Rego (Conftest) | składnia, której mało kto zna | stara składnia Rego (bez `if` i `contains`, sprzed OPA 1.0), reguła nigdy nie sprawdzona na złym przykładzie |
| interpretacja wyników | tłumaczenie `trivy` / `plan` na ludzki | pominięcie `must be replaced` w długim planie |

Zasada: wynik każdej bramki wraca do AI jako kontekst („popraw, `validate` mówi…”), a każda poprawka przechodzi bramki od nowa.

---

## 8. Pytania z sali

- **„Czy `validate` wystarczy?”** — Nie. Sprawdza schemat, nie bezpieczeństwo ani sens. `0.0.0.0/0` jest poprawnym stringiem.
- **„Po co test, skoro jest Trivy?”** — Trivy zna ogólne reguły. Nie wie, że *Wasz* bucket ma mieć wersjonowanie, a rola orders-api tylko `sqs:SendMessage` na jednej kolejce.
- **„Test czy polityka?”** — Test pilnuje jednego modułu. Polityka pilnuje każdej zmiany w każdym repo.
- **„Czy mock gwarantuje, że AWS to przyjmie?”** — Nie. Mock sprawdza logikę modułu; czy AWS przyjmie — `plan` na prawdziwym providerze albo `apply`.
- **„`plan` w CI bez kluczy?”** — Rola read-only przez OIDC (lab z 2.2). `plan` bez stanu (`-refresh=false`, stan lokalny) jak w `d2-t1-01/zrob-plan.sh` — tylko do dema.
- **„A Terratest?”** — Stawia prawdziwą infrastrukturę: łapie to, czego mock nie złapie, ale kosztuje minuty i pieniądze, a AI pisze go w Go — trzeba umieć Go, żeby go ocenić.
- **„Kyverno do Terraform?”** — Nie. Kyverno to polityki dla Kubernetesa (manifesty, chart). Dla Terraform: Conftest/OPA albo Sentinel.

---

## Źródła

- `terraform test`, `mock_provider`: https://developer.hashicorp.com/terraform/language/tests i https://developer.hashicorp.com/terraform/language/tests/mocking
- `terraform validate`: https://developer.hashicorp.com/terraform/cli/commands/validate
- Warunki (`validation`, `precondition`, `postcondition`, `check`): https://developer.hashicorp.com/terraform/language/validate
- TFLint i ruleset AWS: https://github.com/terraform-linters/tflint · https://github.com/terraform-linters/tflint-ruleset-aws
- Trivy (misconfiguration, Terraform i plan JSON): https://trivy.dev/latest/docs/scanner/misconfiguration/
- Checkov: https://www.checkov.io/
- Kyverno (CLI, `ValidatingPolicy`, kotwice): https://kyverno.io/docs/ · migracja do CEL: https://kyverno.io/docs/guides/migration-to-cel/
- ValidatingAdmissionPolicy: https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/
- Conftest: https://www.conftest.dev/ · OPA/Terraform: https://www.openpolicyagent.org/docs/latest/terraform/
- Terratest: https://terratest.gruntwork.io/
- Notatki i wyniki prób: `demos/d2-t3-03-terraform-validate/narzedzia.md`, `demos/d2-t4-01-terraform-test/narzedzia.md` + `wyniki/`, `demos/d2-t4-02-kyverno-z-ai/wyniki/`
