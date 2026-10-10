#!/usr/bin/env bash
# Active l'audit dans le manifest de l'API server généré par kubeadm,
# en AJOUTANT les options, montages et volumes (rien n'est effacé).
# Usage, depuis ~/croustino : sudo solutions/09-audit/activer-audit.sh
set -euo pipefail

MANIFEST=/etc/kubernetes/manifests/kube-apiserver.yaml
POLITIQUE=k8s/audit/audit-policy.yaml

if grep -q -- "--audit-policy-file" "$MANIFEST"; then
  echo "L'audit est déjà activé dans $MANIFEST"; exit 0
fi

mkdir -p /etc/kubernetes/audit /var/log/kubernetes/audit
cp "$POLITIQUE" /etc/kubernetes/audit/policy.yaml
# Sauvegarde hors du dossier manifests (sinon le kubelet lancerait deux API servers)
cp "$MANIFEST" /root/kube-apiserver.yaml.bak

# 1. Les options, juste après « - kube-apiserver »
sed -i '/^    - kube-apiserver$/a\
    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml\
    - --audit-log-path=/var/log/kubernetes/audit/audit.log\
    - --audit-log-maxage=7\
    - --audit-log-maxbackup=3\
    - --audit-log-maxsize=50' "$MANIFEST"

# 2. Les montages, juste après « volumeMounts: »
sed -i '/^    volumeMounts:$/a\
    - mountPath: /etc/kubernetes/audit\
      name: audit-policy\
      readOnly: true\
    - mountPath: /var/log/kubernetes/audit\
      name: audit-log' "$MANIFEST"

# 3. Les volumes, juste après « volumes: »
sed -i '/^  volumes:$/a\
  - hostPath:\
      path: /etc/kubernetes/audit\
      type: DirectoryOrCreate\
    name: audit-policy\
  - hostPath:\
      path: /var/log/kubernetes/audit\
      type: DirectoryOrCreate\
    name: audit-log' "$MANIFEST"

echo "Lignes ajoutées :"
diff /root/kube-apiserver.yaml.bak "$MANIFEST" || true
echo "Sauvegarde : /root/kube-apiserver.yaml.bak — l'API server redémarre dans 1 à 2 minutes."
