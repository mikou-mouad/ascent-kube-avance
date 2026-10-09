# Correction du TP 06 – Helm

Le chart est dans `helm/croustino/`.

- **PVC retrouvé :** un StatefulSet nomme ses PVC `<template>-<statefulset>-<ordinal>`. Le chart garde les noms `data` et `postgres` : le nouveau `postgres-0` réutilise `data-postgres-0`, que `kubectl delete` n'avait pas supprimé.
- **Historique :** dans des Secrets du namespace de la release (`sh.helm.release.v1.<release>.v<révision>`), qui contiennent le manifest rendu et les values.
- **`--set` vs fichier commité :** `--set` n'est connu que de Helm (et perdu au prochain upgrade sans le même `--set`). Le fichier de values versionné est la source de vérité, relue en revue de code : c'est la base du GitOps.
- **Lyon et la capacité :** ajouter LimitRange et ResourceQuota au chart (templates activables par des values) ou les gérer à part, par l'équipe plateforme, au moment de créer le namespace.
