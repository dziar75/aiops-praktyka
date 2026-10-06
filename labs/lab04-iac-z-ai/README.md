# lab04 — IaC z AI: PDB i NetworkPolicy dla Kantyny

**Zasada:** nic nie trafia do klastra bez dwóch zielonych bramek (`kubectl apply --dry-run=server` i `trivy config`). Przed `apply` zawsze `kubectl diff`. Zmieniasz pliki w repo, nie robisz `kubectl edit`.

**Po labie masz:** PDB i NetworkPolicy wygenerowane z AI, sprawdzone i wdrożone na Twój namespace, a Kantyna dalej działa.

## Zanim zaczniesz

- zdrowa Kantyna w Twoim namespace (`setup/check.sh` → `SUKCES: 11/11`)
- Claude Code, `kubectl`, `trivy`, `terraform` ≥ 1.16
- `kubectl-ai` skonfigurowany według karty dostępowej (`OPENAI_ENDPOINT`, klucz LiteLLM)

Dwa nowe zasoby:
- **PodDisruptionBudget (PDB)** pilnuje, żeby przy pracach na węzłach nie zniknęły naraz wszystkie pody serwisu.
- **NetworkPolicy** określa, kto może łączyć się z podem.

## 1. Zapytaj kubectl-ai, czego brakuje (tylko odczyt)

Zmienne `OPENAI_API_KEY` i `OPENAI_ENDPOINT` ustaw według karty dostępowej (sekcja „Dzień 2 · kubectl-ai”).

```bash
kubectl-ai --llm-provider=openai --model=claude-haiku-4-5 --enable-tool-use-shim
```

```text
Jakie zasoby ma Kantyna w moim namespace i czego brakuje do bezpiecznego działania (PDB, NetworkPolicy, limity)?
```

kubectl-ai pyta o zgodę także przy łańcuchu komend (`… && …`). Przeczytaj każdą: zgódź się, gdy wszystkie to `get` albo `describe`. Komendę, która coś zmienia, **odrzuć**.

Sprawdź jedną z jego tez samodzielnie, np. `kubectl get pdb,networkpolicy`.

✅ Wiesz, czego brakuje, i jedną tezę potwierdziłeś sam.

## 2. Wygeneruj pliki z Claude Code

Najpierw zbierz etykiety podów, będą potrzebne w prompcie:

```bash
kubectl get pods --show-labels
```

Poproś Claude Code o dwa pliki:
- `k8s/pdb-orders-api.yaml`: PDB dla orders-api,
- `k8s/netpol-postgres.yaml`: NetworkPolicy, która wpuszcza do Postgresa tylko orders-api na porcie 5432.

W prompcie podaj wersję klastra (1.36), etykiety podów i polecenie „nie stosuj, tylko zapisz pliki”.

✅ Oba pliki są w katalogu `k8s/`.

## 3. Przepuść pliki przez bramki

```bash
kubectl apply --dry-run=server -f k8s/
trivy config k8s/
```

Każdy błąd bramki wklej agentowi jako kontekst do poprawki. Powtarzaj, aż obie bramki przejdą. Wpisz do dziennika, co złapały.

✅ Obie bramki bez błędów.

## 4. Wdróż i sprawdź

`kubectl diff` pokazuje, co dokładnie zmieni się w klastrze. Przeczytaj go przed `apply`. Gdy są różnice, kończy się kodem 1. To nie błąd.

```bash
kubectl diff -f k8s/
kubectl apply -f k8s/
setup/check.sh
```

Jeśli wynik `check.sh` spadnie: postaw hipotezę, sprawdź ją i popraw plik (nie klaster).

✅ `check.sh` → 11/11, a `kubectl get pdb,networkpolicy` pokazuje nowe zasoby.

## 5. To samo w Terraform

Poproś agenta, żeby przepisał NetworkPolicy na zasób `kubernetes_network_policy_v1`:
- provider `kubernetes` z Twoim kubeconfigiem i kontekstem,
- lokalny stan w katalogu `tf/`, plik stanu dopisany do `.gitignore`.

```bash
cd tf
terraform init
terraform validate
terraform plan
```

Porównaj wynik `plan` z tym, co już jest w klastrze. Czego Terraform chce dodać, a co już istnieje? **Nie rób `terraform apply`.**

✅ `plan` działa i umiesz wyjaśnić jego wynik.

## Dziennik

Skopiuj tabelę do pliku `lab04/dziennik.md` w swoim forku.

| # | Bramka / krok | Co złapała (albo co poprawiłem sam) | Poprawka |
|---|---|---|---|
| 1 | | | |

## SUKCES

- [ ] `setup/check.sh` → `SUKCES: 11/11`
- [ ] w klastrze są PDB i NetworkPolicy z plików w Twoim repo (`kubectl get pdb,networkpolicy`)
- [ ] w dzienniku jest co najmniej jedna rzecz, którą złapała bramka albo którą poprawiłeś sam

## Dla chętnych

- **Postgres z AI.** Każ AI napisać StatefulSet, PVC i Secret dla **drugiej** instancji Postgresa o nazwie `postgres-ai` (własne nazwy i etykiety, **nie podmieniaj** bazy Kantyny). Przepuść przez bramki z kroku 3, wdróż i porównaj z tym, co wdraża chart: `helm get manifest kantyna -n <login>`. Patrz na: hasło, PVC, `securityContext`, probe'y, `resources`.
  Limity namespace'u to maks. 3 PVC i 1536Mi `requests.memory` łącznie, a Kantyna część już zajmuje. Daj małe `requests` i PVC 1Gi. Na koniec `kubectl delete -f …` i osobno usuń PVC.
- Ten sam prompt co w kroku 5, ale z Terraform MCP Server. Porównaj liczbę poprawek.
- Poproś kubectl-ai o przeskalowanie orders-api do 2 replik, przeczytaj prośbę o zgodę i **odrzuć**. Zapisz, co by się stało z PDB przy 1 replice.
- `trivy config app/deploy/helm/kantyna`: co znalazł i co z tego jest realnym ryzykiem?

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| kubectl-ai: timeout albo 401 | Zgłoś prowadzącemu swój adres IP. Przy złym kluczu sprawdź kartę |
| kubectl-ai odpowiada jednym zdaniem („Sprawdzę…”) i nic nie uruchamia | Brakuje `--enable-tool-use-shim` |
| `budget exceeded` | Zgłoś prowadzącemu |
| `--dry-run=server` → `forbidden` | Zasób spoza Twoich uprawnień albo zły namespace w pliku |
| `--dry-run=server` → `exceeded quota` | Za duże `requests` albo za dużo PVC w namespace |
| `check.sh` spada po `apply` | Zacznij od `kubectl get networkpolicy -o yaml` i etykiet podów. Szybki powrót: `kubectl delete -f k8s/netpol-postgres.yaml` |
| `terraform plan` → błąd uwierzytelnienia | Provider `kubernetes` musi wskazywać Twój kubeconfig i kontekst (`config_path`, `config_context`) |
