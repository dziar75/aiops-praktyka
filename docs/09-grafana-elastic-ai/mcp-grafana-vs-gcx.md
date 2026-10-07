# Claude Code i Grafana: mcp-grafana czy gcx

Dwa sposoby, żeby asystent AI w terminalu (Claude Code, Cursor, Copilot) sam odpytywał Grafanę: serwer MCP albo zwykłe CLI.

> Stan na 6 października 2026: mcp-grafana 2.0.1, gcx 1.5.0, Grafana 13.2.3. Obie drogi sprawdzone na Grafanie szkoleniowej.


## Na czym polega różnica

```
 Claude Code ──(MCP, narzędzia z opisami)──► mcp-grafana ──► API Grafany ──► Prometheus / Loki / Tempo
 Claude Code ──(Bash: gcx metrics query …)──► gcx ─────────► API Grafany ──► Prometheus / Loki / Tempo
```

W obu przypadkach zapytanie idzie przez API Grafany z Twoim kontem. Asystent nie łączy się bezpośrednio z Prometheusem ani z Loki.

| | mcp-grafana | gcx |
|---|---|---|
| Co to jest | serwer MCP Grafany (open source) | oficjalne CLI Grafany, następca `grafanactl` |
| Jak go używa asystent | wywołuje narzędzia MCP (np. zapytanie Prometheus, zapytanie Loki, wyszukanie dashboardu) | uruchamia komendę w Bash, np. `gcx metrics query '…'` |
| Co widzisz przed zgodą | nazwę narzędzia i jego argumenty | całą komendę z zapytaniem PromQL/LogQL |
| Instalacja | `uv` (`uvx mcp-grafana`) albo Docker | `brew install gcx` albo skrypt / binarka |
| Logowanie | zmienne: `GRAFANA_USERNAME` + `GRAFANA_PASSWORD` albo `GRAFANA_SERVICE_ACCOUNT_TOKEN` | `gcx login` z `--basic-auth`, `--token` albo `--oauth` (Cloud); zapisuje kontekst |
| Bez AI | nie | tak: skrypty, CI, dashboardy i alerty jako kod |
| Ograniczanie | flagi serwera: tylko odczyt, wybrane narzędzia, wymuszone etykiety w Loki | uprawnienia konta Grafany |
| Dashboard | tworzy i edytuje przez narzędzia | z manifestu (`gcx dashboards create`); prościej w UI |
| Działa z | Claude Code, Cursor, Copilot, każdy klient MCP | każdy asystent z terminalem; w trybie agenta sam przełącza się na JSON |

## Kiedy co wybrać

- **gcx**, gdy chcesz widzieć każde zapytanie, nie masz `uv` albo chcesz potem użyć tych samych komend w skrypcie lub CI.
- **mcp-grafana**, gdy asystent ma pracować w wielu krokach (szukanie dashboardów, alertów, przejście z logu do trace'a) albo gdy chcesz twardo ograniczyć jego narzędzia flagami serwera.
- **Na produkcji** oba na koncie tylko do odczytu (Viewer albo service account z wąską rolą). Konto Editor, jak na szkoleniu, pozwala też zmieniać dashboardy i alerty.

## mcp-grafana: opcje

```bash
claude mcp add grafana -e GRAFANA_URL=https://grafana.aiops.marniok.dev \
  -e GRAFANA_USERNAME=<login> -e GRAFANA_PASSWORD='<hasło>' \
  -- uvx mcp-grafana
claude mcp list
```

Przydatne flagi (dopisz po `uvx mcp-grafana`):

| Flaga | Co robi |
|---|---|
| `--disable-write` | wyłącza narzędzia, które tworzą albo zmieniają (dashboardy, alerty, adnotacje) |
| `--enabled-tools prometheus,loki,dashboard` | zostawia tylko wybrane grupy narzędzi |
| `--disable-admin`, `--disable-alerting`, `--disable-…` | wyłącza pojedyncze grupy |
| `--loki-enforced-matchers 'namespace!~"vault\|payments"'` | dokleja etykiety do każdego zapytania Loki (działa razem z `--disable-api`) |

Przykład tylko do odczytu, tylko metryki i logi:

```bash
claude mcp add grafana-ro -e GRAFANA_URL=… -e GRAFANA_USERNAME=… -e GRAFANA_PASSWORD=… \
  -- uvx mcp-grafana --disable-write --enabled-tools prometheus,loki,datasource
```

## gcx: opcje

```bash
brew install gcx        # Linux / WSL: curl -fsSL https://raw.githubusercontent.com/grafana/gcx/main/scripts/install.sh | sh
gcx login szkolenie --server https://grafana.aiops.marniok.dev --basic-auth --user <login>
```

| Komenda | Co robi |
|---|---|
| `gcx metrics query '<PromQL>' -o table` | zapytanie o teraz |
| `gcx metrics query '<PromQL>' --time 2026-10-04T10:15:00Z` | wartość w danej chwili (UTC) |
| `gcx metrics query '<PromQL>' --since 1h` albo `--from … --to … --step 1m` | przebieg w czasie |
| `gcx logs query '<LogQL>' --from … --to … --limit 20 -o table` | logi z okna (przy logach nie ma `--time`) |
| `gcx metrics query '…' --share-link` | link do tego samego zapytania w Explore |
| `gcx datasources list` | źródła danych (gcx wybiera domyślne sam) |
| `gcx dashboards search <tekst>` / `list` | szukanie dashboardów |
| `gcx traces …`, `gcx alert …` | Tempo i reguły alertów |
| `gcx agent skills install` | gotowe instrukcje dla asystentów (katalog `~/.agents/skills`) |

W promptach do Claude Code dopisz: „użyj `gcx metrics query` i `gcx logs query`, pokaż mi zapytanie”.

## Pułapki (z prób na danych Kantyny)

- Etykieta endpointu w metrykach Kantyny to `route`, nie `handler`. W Loki serwis to `app`, nie `app_kubernetes_io_name`. Zła etykieta daje pusty wynik w obu narzędziach.
- Pusty wynik to nie zero. Stosunek błędów przy braku błędów jest pusty, dopiero `or vector(0)` daje 0.
- Godziny w odpowiedziach są często w UTC. Czas polski = UTC + 2 h.

