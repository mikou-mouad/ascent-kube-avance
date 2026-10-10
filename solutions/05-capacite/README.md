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
- **promos sans limite :** le nœud passe en `MemoryPressure`. Deux mécanismes tuent des pods : le noyau (OOM killer, immédiat) et le kubelet (éviction, quand la mémoire disponible passe sous son seuil). Tous les pods étant `BestEffort`, ils sont tous candidats : le plus gros consommateur (`promos`) part en général en premier, mais le back, le front ou PostgreSQL peuvent aussi être tués ou évincés. C'est cette loterie qui fait tomber Croustino en plein rush.
- **promos avec LimitRange :** chaque conteneur reçoit une limite de 256Mi. `stress` tente d'allouer 90 % de la mémoire du nœud : le conteneur est tué (`OOMKilled`) et part en `CrashLoopBackOff`, sans toucher aux autres pods. Une valeur explicite au-dessus de 1Gi est refusée à la création.
- **Quota :** le ReplicaSet ne crée que les pods qui tiennent dans le quota. Les événements montrent `exceeded quota`. Avec un quota CPU/mémoire, tout pod doit déclarer requests et limits (sinon refus) : d'où l'intérêt du LimitRange.
- **CPU vs mémoire :** au-delà de sa limite CPU, le conteneur est ralenti (throttling). Au-delà de sa limite mémoire, il est tué (OOMKilled).
- **Scheduler :** il ne regarde que les **requests** par rapport à l'allocatable du nœud, jamais la consommation réelle.
- **Éviction :** sous pression mémoire, le kubelet évince d'abord les pods `BestEffort`, puis les `Burstable` qui dépassent le plus leurs requests, et les `Guaranteed` en dernier.
