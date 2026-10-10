# Correction du TP 05 – Gestion de la capacité

## YAML prêts à l'emploi

Pour ceux qui n'ont pas réussi à les écrire, dans ce dossier :

- `bonus-hpa-priorite.yaml` : le HorizontalPodAutoscaler du back et la PriorityClass des bonus

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `k8s/10-postgres.yaml`
- `k8s/20-back.yaml`
- `k8s/30-front.yaml`
- `k8s/capacite/limitrange.yaml`
- `k8s/capacite/quota.yaml`

Pour les comparer à votre travail : `diff -r solutions/05-capacite/k8s k8s` (ou `helm`).

Manifests : `k8s/capacite/limitrange.yaml`, `k8s/capacite/quota.yaml`, `resources` dans `k8s/10-postgres.yaml`, `k8s/20-back.yaml`, `k8s/30-front.yaml`.

- **QoS au départ :** `BestEffort` (aucune request ni limit). Ce sont les premiers pods évincés, et le scheduler les place sans tenir compte de leur consommation.
- **Pourquoi Croustino tombe :** `promos` déclare request = limit pour le CPU et la mémoire : il est en QoS `Guaranteed`. Les pods de Croustino ne déclarent rien : ils sont `BestEffort`. Quand le nœud manque de mémoire, le kubelet évince d'abord les pods qui dépassent leurs requests (les `BestEffort` dépassent toujours, puisque leur request vaut 0), et l'OOM killer du noyau vise d'abord les processus `BestEffort` (score d'ajustement 1000, contre -997 pour `Guaranteed`). Résultat : le gros consommateur est protégé, l'application est sacrifiée. Le nœud reçoit aussi la condition `MemoryPressure`, et les pods `BestEffort` ne peuvent plus y être replanifiés.
- **promos avec LimitRange :** le maximum de 1Gi par conteneur s'applique à la création. Les pods de `promos` (plusieurs Gi) sont refusés : le ReplicaSet affiche `FailedCreate ... maximum memory usage per Container is 1Gi`. Le Deployment existe, mais aucun pod ne tourne.
- **Quota :** le ReplicaSet ne crée que les pods qui tiennent dans le quota. Les événements montrent `exceeded quota`. Avec un quota CPU/mémoire, tout pod doit déclarer requests et limits (sinon refus) : d'où l'intérêt du LimitRange.
- **CPU vs mémoire :** au-delà de sa limite CPU, le conteneur est ralenti (throttling). Au-delà de sa limite mémoire, il est tué (OOMKilled).
- **Scheduler :** il ne regarde que les **requests** par rapport à l'allocatable du nœud, jamais la consommation réelle.
- **Éviction :** sous pression mémoire, le kubelet évince d'abord les pods `BestEffort`, puis les `Burstable` qui dépassent le plus leurs requests, et les `Guaranteed` en dernier.
