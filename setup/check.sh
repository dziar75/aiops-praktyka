#!/usr/bin/env bash
# Sprawdza, czy Kantyna w Twoim namespace działa poprawnie.
# Użycie: ./check.sh [namespace]      (domyślnie namespace z bieżącego kontekstu kubectl)
#         ./check.sh --all            (trener: podsumowanie wszystkich uczestników)
# Zmienne: KCTX — kontekst kubectl (domyślnie bieżący)
set -uo pipefail
k() { kubectl ${KCTX:+--context "$KCTX"} "$@"; }

ok=0; total=0; QUIET=0
pass() { ok=$((ok + 1)); total=$((total + 1)); [[ $QUIET == 1 ]] || echo "  ✅ $1"; }
fail() { total=$((total + 1)); [[ $QUIET == 1 ]] || echo "  ❌ $1${2:+ — $2}"; }

check_ns() {
  local ns=$1 d want ready updated current s eps pod out
  ok=0; total=0

  for d in web orders-api payments worker; do
    read -r want ready updated current < <(k -n "$ns" get deploy "kantyna-$d" \
      -o go-template='{{.spec.replicas}} {{or .status.readyReplicas 0}} {{or .status.updatedReplicas 0}} {{or .status.replicas 0}}' 2>/dev/null)
    # go-template z "or … 0": brakujące pola statusu (np. readyReplicas, gdy żaden pod nie jest gotowy) dają 0,
    # zamiast przesuwać kolumny przy read (wcześniej: „gotowe 2/2” przy 0 gotowych podach).
    want=${want:-?}; ready=${ready:-0}; updated=${updated:-0}; current=${current:-0}
    if [[ $want != "?" && $ready == "$want" && $updated == "$want" && $current == "$want" ]]; then
      pass "Deployment kantyna-$d: wszystkie pody gotowe ($ready/$want)"
    else
      fail "Deployment kantyna-$d: wszystkie pody gotowe" "gotowe $ready/$want, w nowej wersji $updated, łącznie $current"
    fi
  done

  read -r want ready < <(k -n "$ns" get sts kantyna-postgres -o go-template='{{.spec.replicas}} {{or .status.readyReplicas 0}}' 2>/dev/null)
  if [[ -n ${want:-} && ${ready:-0} == "$want" ]]; then pass "StatefulSet kantyna-postgres: gotowy"
  else fail "StatefulSet kantyna-postgres: gotowy" "gotowe ${ready:-0}/${want:-?}"; fi

  for s in web orders-api payments postgres; do
    eps=$(k -n "$ns" get endpointslices -l "kubernetes.io/service-name=kantyna-$s" \
      -o jsonpath='{.items[*].endpoints[*].addresses[0]}' 2>/dev/null)
    if [[ -n $eps ]]; then pass "Service kantyna-$s: ma endpointy"
    else fail "Service kantyna-$s: ma endpointy" "brak podów za Service"; fi
  done

  pod=$(k -n "$ns" get pods -l app.kubernetes.io/name=web --field-selector=status.phase=Running \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  if [[ -z $pod ]]; then
    fail "Aplikacja: menu przez web" "brak działającego poda web, nie da się sprawdzić"
    fail "Aplikacja: zamówienie przez web" "brak działającego poda web, nie da się sprawdzić"
  else
    if out=$(k -n "$ns" exec "$pod" -c web -- wget -qO- -T 5 http://127.0.0.1:8080/api/menu 2>&1) && [[ $out == *\"items\"* ]]; then
      pass "Aplikacja: menu przez web"
    else
      fail "Aplikacja: menu przez web" "$(tail -n1 <<<"$out")"
    fi
    if out=$(k -n "$ns" exec "$pod" -c web -- wget -qO- -T 10 --header 'Content-Type: application/json' \
        --post-data '{"employee_id":"lab-check","items":[{"menu_item_id":1,"qty":1}]}' \
        http://127.0.0.1:8080/api/orders 2>&1) && [[ $out == *order_id* ]]; then
      pass "Aplikacja: zamówienie przez web"
    else
      fail "Aplikacja: zamówienie przez web" "$(tail -n1 <<<"$out")"
    fi
  fi
}

if [[ "${1:-}" == "--all" ]]; then
  QUIET=1
  for ns in $(k get ns -l aiops/participant -o jsonpath='{.items[*].metadata.name}'); do
    check_ns "$ns"
    printf '%-10s %2d/%-2d %s\n' "$ns" "$ok" "$total" "$([[ $ok == "$total" ]] && echo ✅ || echo …)"
  done
  exit 0
fi

NS="${1:-$(k config view --minify -o jsonpath='{..namespace}')}"
[[ -n $NS ]] || { echo "Podaj namespace: $0 <login>" >&2; exit 1; }
echo "Kantyna w namespace $NS:"
check_ns "$NS"
echo
if [[ $ok == "$total" ]]; then echo "SUKCES: $ok/$total"; exit 0; fi
echo "Wynik: $ok/$total"; exit 1
