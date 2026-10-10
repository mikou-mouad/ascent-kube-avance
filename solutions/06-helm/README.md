# Correction du TP 06 – Helm

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `helm/croustino/Chart.yaml`
- `helm/croustino/templates/NOTES.txt`
- `helm/croustino/templates/_helpers.tpl`
- `helm/croustino/templates/back.yaml`
- `helm/croustino/templates/configmap.yaml`
- `helm/croustino/templates/front.yaml`
- `helm/croustino/templates/postgres.yaml`
- `helm/croustino/templates/secret.yaml`
- `helm/croustino/templates/serviceaccount.yaml`
- `helm/croustino/values-lyon.yaml`
- `helm/croustino/values-rennes.yaml`
- `helm/croustino/values.yaml`

Pour les comparer à votre travail : `diff -r solutions/06-helm/k8s k8s` (ou `helm`).

Le chart est dans `helm/croustino/`.

- **PVC retrouvé :** un StatefulSet nomme ses PVC `<template>-<statefulset>-<ordinal>`. Le chart garde les noms `data` et `postgres` : le nouveau `postgres-0` réutilise `data-postgres-0`, que `kubectl delete` n'avait pas supprimé.
- **Historique :** dans des Secrets du namespace de la release (`sh.helm.release.v1.<release>.v<révision>`), qui contiennent le manifest rendu et les values.
- **`--set` vs fichier commité :** `--set` n'est connu que de Helm (et perdu au prochain upgrade sans le même `--set`). Le fichier de values versionné est la source de vérité, relue en revue de code : c'est la base du GitOps.
- **Lyon et la capacité :** ajouter LimitRange et ResourceQuota au chart (templates activables par des values) ou les gérer à part, par l'équipe plateforme, au moment de créer le namespace.
