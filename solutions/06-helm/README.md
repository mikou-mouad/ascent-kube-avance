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

Pour les comparer à votre travail : `diff -r solutions/06-helm/helm helm`.

Le chart est dans `helm/croustino/`.

## Étape 2 – Le chart d'exemple

- **`version` / `appVersion` :** `version` est la version du chart lui-même, à incrémenter à chaque modification des templates. `appVersion` est la version de l'application déployée, à titre d'information.
- **`values.yaml` :** les valeurs par défaut des paramètres du chart. On les surcharge avec `-f mon-fichier.yaml` ou `--set`.
- **`replicaCount` :** dans `templates/deployment.yaml`, `replicas: {{ .Values.replicaCount }}`, à l'intérieur d'un `{{- if not .Values.autoscaling.enabled }}` (si l'autoscaling est activé, c'est le HPA qui décide).
- **`demo.fullname` :** calcule le nom des objets à partir du nom de la release et du chart (`<release>-<chart>`, tronqué à 63 caractères). Tous les templates l'utilisent : deux releases du même chart dans un namespace ne se marchent pas dessus.
- **`NOTES.txt` :** un template affiché à la fin de `helm install` et `helm upgrade` (mode d'emploi, URL…).
- **`--set replicaCount=3` :** surcharge une value pour cette commande, sans modifier de fichier : le YAML rendu contient `replicas: 3`.
- **`lyon-demo` :** c'est `demo.fullname` avec la release `lyon`. Le chart Croustino, lui, garde des noms fixes (`postgres`, `back`, `front`) : une seule release par namespace, et `postgres-0` retrouve son PVC.

## Étapes 3 à 6

- **PVC retrouvé :** un StatefulSet nomme ses PVC `<template>-<statefulset>-<ordinal>`. Le chart garde les noms `data` et `postgres` : le nouveau `postgres-0` réutilise `data-postgres-0`, que `kubectl delete` n'avait pas supprimé.
- **Historique :** dans des Secrets du namespace de la release (`sh.helm.release.v1.<release>.v<révision>`), qui contiennent le manifest rendu et les values.
- **`--set` vs fichier commité :** `--set` n'est connu que de Helm (et perdu au prochain upgrade sans le même `--set`). Le fichier de values versionné est la source de vérité, relue en revue de code : c'est la base du GitOps.
- **Lyon et la capacité :** ajouter LimitRange et ResourceQuota au chart (templates activables par des values) ou les gérer à part, par l'équipe plateforme, au moment de créer le namespace.
