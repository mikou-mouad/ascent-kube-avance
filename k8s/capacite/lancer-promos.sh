#!/usr/bin/env bash
# Déploie promos : chaque pod réserve et consomme presque toute la mémoire
# encore libre d'un worker (mémoire allouable moins les requests déjà posées).
# Arrêt : kubectl delete deployment promos -n croustino
set -euo pipefail
cd "$(dirname "$0")"

# Quantité Kubernetes (Ki, Mi, Gi, k, M, G, octets) -> Mi
en_mi() {
  awk -v q="$1" 'BEGIN {
    n = q + 0; u = q; sub(/^[0-9.]+/, "", u)
    f["Ki"] = 1/1024; f["Mi"] = 1; f["Gi"] = 1024; f["Ti"] = 1048576
    f["k"] = 1000/1048576; f["M"] = 1000000/1048576; f["G"] = 1e9/1048576; f[""] = 1/1048576
    printf "%d", n * f[u] }'
}

libre_min=""
for noeud in $(kubectl get nodes -l '!node-role.kubernetes.io/control-plane' -o name); do
  alloue=$(en_mi "$(kubectl get "$noeud" -o jsonpath='{.status.allocatable.memory}')")
  demande=$(en_mi "$(kubectl describe "$noeud" | awk '/Allocated resources/ {f = 1} f && $1 == "memory" {print $2; exit}')")
  libre=$((alloue - demande))
  echo "${noeud#node/} : ${alloue} Mi allouables, ${demande} Mi déjà réservés, ${libre} Mi libres"
  if [ -z "$libre_min" ] || [ "$libre" -lt "$libre_min" ]; then libre_min=$libre; fi
done

memoire=$((libre_min - 64))
stress=$((memoire - 32))
echo "promos : ${memoire} Mi réservés par pod, ${stress} Mi consommés"
sed -e "s/__MEMOIRE__/${memoire}Mi/g" -e "s/__STRESS__/${stress}M/g" promos.yaml | kubectl apply -f -
