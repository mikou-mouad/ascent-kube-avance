# Correction du TP 05 – Gestion de la capacité

Manifests : `k8s/capacite/limitrange.yaml`, `k8s/capacite/quota.yaml`, `resources` dans `k8s/10-postgres.yaml`, `k8s/20-back.yaml`, `k8s/30-front.yaml`.

- **QoS au départ :** `BestEffort` (aucune request ni limit). Ce sont les premiers pods évincés, et le scheduler les place sans tenir compte de leur consommation.
- **promos avec LimitRange :** chaque conteneur reçoit une limite de 256Mi. `stress` tente d'allouer 1500M : le conteneur est tué (`OOMKilled`) et part en `CrashLoopBackOff`, sans toucher aux autres pods. Une valeur explicite au-dessus de 1Gi est refusée à la création.
- **Quota :** le ReplicaSet ne crée que les pods qui tiennent dans le quota. Les événements montrent `exceeded quota`. Avec un quota CPU/mémoire, tout pod doit déclarer requests et limits (sinon refus) : d'où l'intérêt du LimitRange.
- **CPU vs mémoire :** au-delà de sa limite CPU, le conteneur est ralenti (throttling). Au-delà de sa limite mémoire, il est tué (OOMKilled).
- **Scheduler :** il ne regarde que les **requests** par rapport à l'allocatable du nœud, jamais la consommation réelle.
- **Éviction :** sous pression mémoire, le kubelet évince d'abord les pods `BestEffort`, puis les `Burstable` qui dépassent le plus leurs requests, et les `Guaranteed` en dernier.
