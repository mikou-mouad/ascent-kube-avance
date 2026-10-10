# Correction du TP 07 – Monitoring

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `helm/croustino/dashboards/rush-du-matin.json`
- `helm/croustino/templates/monitoring.yaml`
- `helm/croustino/values-rennes.yaml`
- `helm/croustino/values.yaml`

Pour les comparer à votre travail : `diff -r solutions/07-monitoring/helm helm`.

ServiceMonitor, alertes et dashboard : `helm/croustino/templates/monitoring.yaml` et `helm/croustino/dashboards/rush-du-matin.json`.
Le monitoring est activé pour Rennes dans `values-rennes.yaml` (`monitoring.enabled: true`).

- **`...SelectorNilUsesHelmValues: false` :** par défaut, Prometheus ne prend que les ServiceMonitors portant le label de la release `kps`. Avec `false`, il prend ceux de tous les namespaces, dont celui de Croustino.
- **Cibles DOWN :** `kube-scheduler`, `kube-controller-manager`, `etcd` (et parfois `kube-proxy`) écoutent sur `127.0.0.1` dans un cluster kubeadm. Prometheus ne peut pas les joindre depuis un pod. Pour les surveiller : changer `--bind-address` / `--listen-metrics-urls` ou désactiver ces cibles (`kubeEtcd.enabled: false`…).
- **Requêtes :**
  - `sum by (produit) (rate(croustino_commandes_total[1m])) * 60`
  - `sum(rate(croustino_commandes_rejetees_total[5m])) / (sum(rate(croustino_commandes_rejetees_total[5m])) + sum(rate(croustino_commandes_total[5m])))`
  - `sum by (pod) (container_memory_working_set_bytes{namespace="croustino", container!=""})`
  - `sum by (pod) (kube_pod_container_status_restarts_total{namespace="croustino"})`
- **Pull :** Prometheus connaît la liste des cibles (découverte via l'API Kubernetes), détecte une cible muette (`up == 0`) et maîtrise sa charge. Les applications n'ont pas besoin de connaître le serveur de monitoring.
- **`rate()` :** un compteur ne fait que croître et repart à zéro au redémarrage du pod. `rate()` donne une vitesse et gère ces remises à zéro.
- **Autres alertes utiles :** base indisponible (`/readyz` en échec, pods non prêts), latence ou erreurs 5xx du front, PVC presque plein, nœud en pression mémoire, certificat proche de l'expiration.
