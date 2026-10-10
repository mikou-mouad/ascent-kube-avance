# Correction du TP 03 – Stockage

## YAML prêts à l'emploi

Pour ceux qui n'ont pas réussi à les écrire, dans ce dossier :

- `test-pvc.yaml` : le PVC de test de l'étape 3
- `conso-pod.yaml` : le pod qui l'utilise (équivalent du `kubectl run --overrides`) : `kubectl apply -f solutions/03-stockage/conso-pod.yaml`
- `bonus-storageclass-retain.yaml` : la StorageClass du bonus

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `k8s/10-postgres.yaml`

Pour les comparer à votre travail : `diff -r solutions/03-stockage/k8s k8s` (ou `helm`).

Le StatefulSet est dans `k8s/10-postgres.yaml`.

- **Incident :** sans volume, les données vivent dans la couche inscriptible du conteneur. Elles disparaissent avec le pod.
- **reclaimPolicy `Delete` :** quand le PVC est supprimé, le PV et les données le sont aussi.
- **WaitForFirstConsumer :** le volume n'est créé qu'une fois un pod planifié, sur le nœud de ce pod. Indispensable pour un stockage local.
- **PVC de test :** `Pending` tant qu'aucun pod ne l'utilise. Après suppression du PVC, le PV est supprimé (politique `Delete`).
- **StatefulSet plutôt que Deployment :** identité stable (`postgres-0`), un PVC dédié par réplica via `volumeClaimTemplates`, démarrage et arrêt ordonnés. Un Deployment avec un seul PVC RWO bloquerait au rolling update (deux pods voudraient le même volume).
- **Suppression du StatefulSet :** les PVC sont conservés (par défaut). En recréant le StatefulSet, `postgres-0` retrouve `data-postgres-0`. Supprimer le PVC détruit les données.
- **Perte du nœud :** avec local-path, le volume est lié au nœud : le pod reste `Pending` et les données sont perdues si le disque l'est. En production : stockage réseau ou distribué (Ceph/Rook, Longhorn, CSI du cloud), sauvegardes, ou base managée / opérateur avec réplication (CloudNativePG).
- **Bonus 2 réplicas :** `postgres-1` et `data-postgres-1` apparaissent, mais ce sont deux bases indépendantes : un StatefulSet ne réplique pas les données.
