# Materiały

Tematy w kolejności ze szkolenia. W każdym katalogu: opis (`.md`) i diagram `architektura.html` (pobierz i otwórz w przeglądarce).

| # | Temat | Opis | Diagram |
|---|---|---|---|
| 00 | Środowisko szkoleniowe: AWS, Kubernetes, Kantyna, narzędzia | — | [architektura.html](00-srodowisko/architektura.html) |
| 01 | Asystenci AI do kodu — GitHub Copilot, Claude Code i OpenAI Codex | [asystenci-ai.md](01-asystenci-ai/asystenci-ai.md) | [architektura.html](01-asystenci-ai/architektura.html) |
| 02 | LiteLLM — brama do modeli AI (AI gateway) | [litellm.md](02-litellm/litellm.md) | [architektura.html](02-litellm/architektura.html) |
| 03 | k8sgpt — skaner klastra Kubernetes z wyjaśnieniami AI | [k8sgpt.md](03-k8sgpt/k8sgpt.md) | [architektura.html](03-k8sgpt/architektura.html) |
| 04 | Robusta i HolmesGPT — alerty z kontekstem i agent śledczy | [robusta.md](04-robusta/robusta.md) | [architektura.html](04-robusta/architektura.html) |
| 05 | Claude Code — bezpieczeństwo i uprawnienia agenta | [claude-code-security.md](05-claude-code-security/claude-code-security.md) | [architektura.html](05-claude-code-security/architektura.html) |
| 06 | Generowanie konfiguracji — kubectl-ai i AI dla Terraform („Terraform Copilot”) | [kubectl-ai-terraform.md](06-kubectl-ai-terraform/kubectl-ai-terraform.md) | [architektura.html](06-kubectl-ai-terraform/architektura.html) |
| 07 | Walidacja, testy i polityki IaC — co do czego służy | [testowanie-terraform.md](07-testowanie-terraform/testowanie-terraform.md) | — |
| 08 | GitHub Actions: tag czy SHA — skąd pipeline bierze cudzy kod | [tagi-sha.md](08-github-actions-tagi-sha/tagi-sha.md) | [architektura.html](08-github-actions-tagi-sha/architektura.html) |
| 09 | Grafana AI i Elastic AI — asystenci AI w platformach observability | [grafana-elastic-ai.md](09-grafana-elastic-ai/grafana-elastic-ai.md) | [architektura.html](09-grafana-elastic-ai/architektura.html) |
| 09 | Claude Code i Grafana: mcp-grafana czy gcx | [mcp-grafana-vs-gcx.md](09-grafana-elastic-ai/mcp-grafana-vs-gcx.md) | [architektura.html](09-grafana-elastic-ai/architektura.html) |
| 10 | Wykrywanie anomalii — Azure Monitor, Grafana ML i AWS | [anomaly-detection.md](10-anomaly-detection/anomaly-detection.md) | [architektura.html](10-anomaly-detection/architektura.html) |
| 11 | AI Agents i automatyzacja — LangChain i OpenAI (Assistants API → Responses API / Agents SDK) | [ai-agents.md](11-ai-agents/ai-agents.md) | [architektura.html](11-ai-agents/architektura.html) |
| 12 | Security AI — Trivy i GitHub Advanced Security | [security-trivy-ghas.md](12-security-trivy-ghas/security-trivy-ghas.md) | [architektura.html](12-security-trivy-ghas/architektura.html) |
| 13 | Stack observability: metryki, logi, ślady i alerty | [stack-observability.md](13-stack-observability/stack-observability.md) | [architektura.html](13-stack-observability/architektura.html) |

## Szablony promptów

[`prompts/`](prompts/): diagnoza, wyjaśnienie, generowanie konfiguracji, review zmiany, komunikat incydentu, post-mortem, grupowanie alertów.
