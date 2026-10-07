# lab05 — Pytaj dane językiem naturalnym, sprawdzaj zapytania, zbuduj dashboard

**Zasada:** zapytanie jest dobre dopiero wtedy, gdy zwraca dane, które umiesz wyjaśnić.

**Po labie masz:** dashboard w swoim folderze Grafany i listę godzin, w których w Kantynie działo się coś dziwnego. Lista przyda się w następnym temacie.

Pracujesz na namespace **`demo`**: Kantyna pod stałym ruchem, z historią z kilku ostatnich dni.

## Zanim zaczniesz

- Grafana: `https://grafana.aiops.marniok.dev`, login i hasło z karty
- Claude Code
- `gcx` albo `uv` (dla mcp-grafana), instalacja w kroku 1. `uv`: macOS `brew install uv`, Linux / WSL `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 1. Podłącz Grafanę do Claude Code

Dzięki temu asystent sam wykonuje zapytania w Grafanie i widzi wyniki. Wybierz jedną drogę (porównanie: `docs/09-grafana-elastic-ai/mcp-grafana-vs-gcx.md`).

**A. gcx (CLI Grafany).** Claude Code uruchamia `gcx` jak każdą komendę, więc widzisz każde zapytanie, zanim je zatwierdzisz.

```bash
brew install gcx          # Linux / WSL: curl -fsSL https://raw.githubusercontent.com/grafana/gcx/main/scripts/install.sh | sh
gcx login szkolenie --server https://grafana.aiops.marniok.dev --basic-auth --user <login>
gcx metrics query 'sum by (route) (rate(http_requests_total{namespace="demo"}[5m]))' -o table
```

W promptach do Claude Code dopisuj: „użyj `gcx metrics query` i `gcx logs query`”.

**B. mcp-grafana (serwer MCP).** Asystent dostaje gotowe narzędzia Grafany (wymaga `uv`).

```bash
claude mcp add grafana -e GRAFANA_URL=https://grafana.aiops.marniok.dev \
  -e GRAFANA_USERNAME=<login> -e GRAFANA_PASSWORD='<hasło z karty>' \
  -- uvx mcp-grafana
claude mcp list
```

Żadna nie działa po 5 minutach? Claude Code pisze zapytanie, a Ty wklejasz je w Grafanie (**Explore**).

✅ `gcx metrics query` zwraca liczby albo `claude mcp list` pokazuje `grafana … Connected` (albo masz otwarte Explore).

## 2. Jak Kantyna działa teraz

Zapytaj o ostatnią godzinę w namespace `demo`, np.:

```text
Używając Grafany (Prometheus), pokaż dla namespace demo z ostatniej godziny:
ruch req/s per endpoint orders-api, odsetek odpowiedzi 5xx, p95 czasu odpowiedzi
POST /api/orders i liczbę wiadomości w kolejce workera. Do każdej liczby podaj zapytanie PromQL.
```

Każde zapytanie sprawdź w Explore. Czy metryka i etykiety istnieją (**Metrics browser**)? Czy wynik ma sens?

✅ Masz 3–4 zapytania, które sprawdziłeś w Explore i umiesz powiedzieć, co liczą.

## 3. Znajdź dziwne momenty w historii

Kantyna w `demo` działa od kilku dni. Znajdź momenty, w których coś odbiegało od normy: błędy, czas odpowiedzi, pamięć, restarty, kolejka.

```text
Przejrzyj namespace demo z ostatnich 4 dni. Kiedy błędy, p95, pamięć podów, restarty albo
kolejka workera wyraźnie odbiegały od normy? Podaj godziny w czasie polskim i zapytanie,
które to pokazuje.
```

Każdy moment potwierdź sam: wykres w Explore (zakres „Last 4 days”) i logi z tego okna (Loki):

```logql
{namespace="demo", app="orders-api"} | json | level="ERROR"
```

Zapisz momenty w pliku `labs/lab05-observability/momenty.md`:

```text
<dzień gg:mm–gg:mm> | <co widać, z liczbą> | <zapytanie PromQL albo LogQL>
```

✅ Masz co najmniej 3 momenty z godziną (czas polski), opisem i zapytaniem.

## 4. Zbuduj dashboard

Weź 3–4 najlepsze zapytania z kroków 2 i 3 i zbuduj z nich dashboard. Możesz poprosić asystenta (przy mcp-grafana) albo zrobić to ręcznie: **Dashboards → New**.

Zapisz go w folderze `<login>`. Każdy panel ma mieć tytuł, jednostkę (req/s, %, s, MiB) i czytelną legendę.

✅ Dashboard zapisany w Twoim folderze, wszystkie panele pokazują dane.

## 5. Dla chętnych

- Poproś asystenta o regułę alertu dla jednego panelu. Zapytaj, skąd wziął próg, i porównaj go z danymi z ostatnich 4 dni.
- „Streść najczęstsze wzorce błędów w logach orders-api z wybranego okna” i porównaj odpowiedź z Loki → **Patterns** (Explore → Logs).
- W logu z błędem znajdź `trace_id`, otwórz trace w Tempo i zapytaj asystenta, który span był najwolniejszy.

## SUKCES

- [ ] co najmniej 3 zapytania z kroku 2 sprawdzone w Explore
- [ ] w `momenty.md` co najmniej 3 momenty: godzina (czas polski), co widać, zapytanie
- [ ] dashboard z co najmniej 3 działającymi panelami w folderze `<login>`

## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Grafana nie odpowiada (timeout) | Twój adres IP nie jest na liście; `curl -4 ifconfig.me` i podaj wynik na czacie |
| `uvx: command not found` | zainstaluj `uv` (wyżej) albo użyj gcx |
| `gcx: command not found` po skrypcie instalacyjnym | otwórz nowy terminal albo dopisz katalog podany przez skrypt do `PATH` |
| gcx: `Unknown flag --time` przy logach | `gcx logs query` przyjmuje zakres: `--from 2026-10-04T10:00:00Z --to 2026-10-04T11:00:00Z` (`--time` działa tylko w `metrics query`) |
| `grafana` w `claude mcp list` nie łączy się | sprawdź login i hasło z karty oraz adres z `https://`; usuń i dodaj ponownie: `claude mcp remove grafana` |
| zapytanie zwraca pusty wynik | otwórz Metrics browser: czy ta metryka i te etykiety istnieją? Etykieta endpointu to `route` |
| asystent mówi „brak błędów”, a wynik jest pusty | pusty wynik ≠ zero; dopisz `or vector(0)` albo sprawdź okno czasu |
| godziny od asystenta nie zgadzają się z wykresem | model często podaje UTC; czas polski = UTC + 2 h (po 25.10 UTC + 1 h) |
| nie da się zapisać zmian w gotowym dashboardzie | gotowe dashboardy są tylko do odczytu; **Save as** do swojego folderu |
