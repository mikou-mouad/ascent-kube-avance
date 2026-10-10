# TP 07 – « On l'a appris sur les réseaux sociaux »

**Durée :** 1 h (10 min le jour 2, 50 min le jour 3) · **Branche :** `tp-07-monitoring` · **Correction :** branche `tp-08-logs` (`helm/croustino/templates/monitoring.yaml`)

## L'incident

> Lundi, 7h40. Un client publie : « Croustino, 3 commandes refusées ce matin, vous êtes sérieux ? »
> Inès découvre le problème en lisant le message. Le back rejetait des commandes depuis 40 minutes, et personne n'avait de chiffres : combien de commandes, combien de rejets, depuis quand ?

## Objectifs

- Installer la stack Prometheus / Grafana / Alertmanager avec Helm.
- Faire collecter les métriques de l'application avec un ServiceMonitor.
- Écrire des requêtes PromQL.
- Construire un dashboard et une alerte, et les livrer avec le chart Croustino.

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-07-monitoring
```

La branche contient l'état attendu à la fin du TP précédent (c'est aussi sa correction).
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Jour 2 – Lancer l'installation (10 min)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kps prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f k8s/monitoring/values-kps.yaml
kubectl get pods -n monitoring -w
```

Lisez `k8s/monitoring/values-kps.yaml` pendant l'installation : à quoi servent les options `...SelectorNilUsesHelmValues: false` ?

## Jour 3 – Exploiter (50 min)

### 1. Découvrir Prometheus

Ouvrez Prometheus sur `http://<IP d'un nœud>:30090`, menu **Status > Targets**.

**Questions :** quelles cibles sont `DOWN` ? Pourquoi (indice : regardez l'adresse d'écoute de `kube-scheduler` et `etcd` dans `/etc/kubernetes/manifests/`) ? Est-ce grave pour la formation ?

### 2. Les métriques de Croustino

Le back expose ses métriques :

```bash
kubectl run test --rm -it --image=curlimages/curl --restart=Never -n croustino -- \
  curl -s http://back:8080/metrics
```

Créez un **ServiceMonitor** dans le chart (`helm/croustino/templates/monitoring.yaml`), activable par la valeur `monitoring.enabled` :

- il sélectionne le Service `back` (label `app: back`) ;
- il collecte le port `http`, chemin `/metrics`, toutes les 15 s.

```bash
helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml --set monitoring.enabled=true
```

Vérifiez que la cible `serviceMonitor/croustino/back` apparaît dans Prometheus.

### 3. Simuler le rush et écrire du PromQL

```bash
kubectl apply -f k8s/charge/rush-du-matin.yaml
```

Dans **Graph**, écrivez les requêtes suivantes :

| Question | Indice |
|----------|--------|
| Commandes enregistrées par minute, par produit | `rate(croustino_commandes_total[1m])` |
| Taux de rejet (en %) | rejets / (rejets + commandes) |
| Mémoire de chaque pod de `croustino` | `container_memory_working_set_bytes` |
| Redémarrages des conteneurs de `croustino` | `kube_pod_container_status_restarts_total` |

### 4. Le dashboard « Rush du matin »

Grafana : `http://<IP d'un nœud>:30300` (admin / croustino).
Créez un dashboard avec au moins 3 panneaux à partir de vos requêtes. Explorez aussi les dashboards fournis (**Kubernetes / Compute Resources / Namespace (Pods)**).

Exportez votre dashboard en JSON (**Share > Export**) : il sera livré par le chart sous forme de ConfigMap portant le label `grafana_dashboard: "1"`.

### 5. L'alerte

Ajoutez au chart une **PrometheusRule** `CroustinoRejetsEleves` : plus de 10 commandes rejetées en 5 minutes, pendant 1 minute.
Relancez le rush (`kubectl delete job rush-du-matin` puis `kubectl apply …`) et suivez l'alerte dans **Alerts** (Pending → Firing), puis dans Alertmanager (`:30093`).

## Questions de fin

1. Pourquoi Prometheus « tire » les métriques (pull) au lieu de les recevoir ?
2. Pourquoi utiliser `rate()` sur un compteur plutôt que sa valeur brute ?
3. Quelles autres alertes Croustino devrait-il avoir ?

## Bonus

- Ajoutez une alerte `CroustinoBackRedemarre` sur les redémarrages du back et provoquez-la (`kubectl exec deploy/back -- sh -c 'kill 1'`).
- Envoyez les alertes vers un webhook de test (configuration d'Alertmanager).
- Activez le monitoring pour Lyon et filtrez le dashboard par namespace avec une variable.
