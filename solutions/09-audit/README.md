# Correction du TP 09 – Audit

## YAML prêts à l'emploi

Pour ceux qui n'ont pas réussi à les écrire, dans ce dossier :

- `kube-apiserver-audit.yaml` : extrait de `/etc/kubernetes/manifests/kube-apiserver.yaml` avec l'audit activé (lignes `# AJOUT`)
- la politique d'audit elle-même : `k8s/audit/audit-policy.yaml`

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :


Pour les comparer à votre travail : `diff -r solutions/09-audit/k8s k8s` (ou `helm`).

Politique : `k8s/audit/audit-policy.yaml`. Modifications du static pod : voir l'énoncé.

## Niveaux

- Lecture d'un Secret : `Metadata` (règle 2, avant la règle des lectures).
- Suppression d'un Deployment dans `croustino` : `RequestResponse` (règle 4).
- Création d'un namespace : `Metadata` (règle 5, ressource sans namespace).
- Secrets en `RequestResponse` : le contenu des Secrets serait écrit en clair dans le fichier d'audit.

## Enquête

```bash
A=/var/log/kubernetes/audit/audit.log

# 1. Le coupable
sudo jq -c 'select(.verb=="delete" and .objectRef.resource=="deployments" and .objectRef.name=="back" and .responseStatus.code < 300)
  | {t: .requestReceivedTimestamp, qui: .user.username, groupes: .user.groups, ip: .sourceIPs, outil: .userAgent}' $A

# 2. Les refus
sudo jq -c 'select(.responseStatus.code == 403)
  | {qui: .user.username, verbe: .verb, ressource: .objectRef.resource, ns: .objectRef.namespace}' $A

# 3. Le scaling du front
sudo jq -c 'select(.objectRef.resource=="deployments" and .objectRef.subresource=="scale" and .verb=="patch")
  | {qui: .user.username, replicas: .requestObject.spec.replicas}' $A

# 4. Événements par utilisateur
sudo jq -r '.user.username' $A | sort | uniq -c | sort -rn
```

Réponse : **malik** (groupe `dev`), via `kubectl`, depuis l'IP du control plane. Théo a essayé avant lui mais a été refusé (403).

## Questions

- **Volume :** quelques Mo en 30 minutes sur ce petit cluster, surtout à cause des contrôleurs. En `RequestResponse` partout, chaque lecture (dont les `list` de milliers d'objets) serait écrite en entier : des Go par heure, de la latence sur l'API server et un risque pour le disque du control plane.
- **Système externe :** un attaquant administrateur du cluster pourrait effacer le fichier local. Il faut aussi conserver, rechercher et alerter (SIEM, Elasticsearch).
- **Prévention :** l'audit sert à comprendre, pas à empêcher. Il faut en plus : RBAC plus strict (Malik n'a pas besoin de supprimer des Deployments en prod, la CI s'en charge), GitOps, protections contre la suppression (admission policy), alertes sur les suppressions en prod.
