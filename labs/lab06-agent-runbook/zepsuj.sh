#!/usr/bin/env bash
# Psuje Kantynę w Twoim namespace: orders-api zwraca 500 na każde żądanie /api/
# (flaga error_rate w ConfigMap kantyna-flags). Działa na Twoim koncie, nie na koncie agenta.
set -euo pipefail
kubectl get configmap kantyna-flags -o jsonpath='{.data.flags\.json}' \
  | python3 -c 'import json,sys; f=json.load(sys.stdin); f["orders-api"]["error_rate"]=1.0; print(json.dumps({"data":{"flags.json":json.dumps(f,indent=2)}}))' \
  | kubectl patch configmap kantyna-flags --type merge --patch-file /dev/stdin
echo "Zepsute. Za ok. 1 min orders-api zacznie zwracać 500 (setup/check.sh)."
