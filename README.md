# AIOps w praktyce — repo ćwiczeniowe

Szkolenie Sages, 5–7.10.2026. Przez trzy dni pracujemy na aplikacji **Kantyna** (system zamawiania obiadów w firmowej stołówce), która działa na klastrze EKS. W każdym labie używamy narzędzi AI do diagnozy, konfiguracji i obsługi incydentów.

## Na start

1. Zrób **fork** tego repo i sklonuj swój fork: [`setup/README.md`](setup/README.md#0-twoja-kopia-repo-fork).
2. Przygotuj stanowisko (dalsze kroki w [`setup/README.md`](setup/README.md)).
3. Sprawdź, czy Twoja Kantyna działa: `setup/check.sh` → `SUKCES: 11/11`.

Mapa środowiska (AWS, Kubernetes, Kantyna, narzędzia): [`docs/00-srodowisko/architektura.html`](docs/00-srodowisko/architektura.html) — otwórz plik ze swojego klona w przeglądarce.

## Każdego dnia o 9:00

Laby z danego dnia są w repo prowadzącego na początku zajęć:

```bash
git add -A && git commit -m "moja praca"   # najpierw zapisz swoje zmiany (jeśli są)
git pull upstream main                      # pobierz nowe laby i materiały
git push                                    # wypchnij do swojego forka
```

## Co jest w repo

| Katalog | Co tam jest |
|---|---|
| [`setup/`](setup/) | przygotowanie stanowiska i `check.sh` |
| [`app/`](app/) | aplikacja Kantyna: kod, chart Helm, runbooki ([opis](app/README.md)) |
| [`labs/`](labs/) | laboratoria: cel, kroki, warunek SUKCES |
| [`docs/`](docs/) | materiały do tematów i [szablony promptów](docs/prompts/) |

## Plan

Zajęcia codziennie **9:00–17:00**.

| Dzień | Temat | Laby |
|---|---|---|
| pon 5.10 | Fundamenty i diagnostyka | [lab01 — Rozgrzewka w Claude Code](labs/lab01-rozgrzewka-claude-code/) · [lab01b — Prompt, który da się sprawdzić](labs/lab01b-prompty/) · [lab02 — Debugging z AI](labs/lab02-debugging-z-ai/) |
| wt 6.10 | Zmiana, pipeline'y i infrastruktura | [lab03 — Pipeline z AI](labs/lab03-pipeline-z-ai/) · [lab03b — Skill: przegląd PR-a z terminala](labs/lab03b-skill-przeglad-pr/) · [lab04 — IaC z AI](labs/lab04-iac-z-ai/) |
| śr 7.10 | Observability, automatyzacja i bezpieczeństwo | [lab05 — Observability](labs/lab05-observability/) · [lab06 — Agent z runbookiem](labs/lab06-agent-runbook/) · [lab06b — Trivy z AI](labs/lab06b-trivy-z-ai/) · [lab07 — Capstone](labs/lab07-capstone/) |

## Zasady

- AI to junior do weryfikacji: każdą hipotezę i każdą komendę sprawdzasz, zanim ją zatwierdzisz.
- Do modelu nie wysyłasz haseł, kluczy ani danych osobowych. `app/.env` zawiera **fałszywe** sekrety, do ćwiczeń.
- Pracujesz tylko w swoim namespace. Klaster jest wspólny.
- Problem techniczny (dostęp, logowanie, limit zapytań) zgłaszasz od razu.
