# TP 07 – « On l'a appris sur les réseaux sociaux »

**Durée :** 1 h (10 min le jour 2, 50 min le jour 3) · **Branche :** `tp-07-monitoring` · **Correction :** `solutions/07-monitoring/`, dans cette branche

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

La branche contient l'état attendu à la fin du TP précédent. La correction de ce TP est dans `solutions/07-monitoring/`.
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

Vérifiez que Prometheus collecte bien le back. Dans le navigateur de ClientWeb, sur `http://10.10.0.11:30090` :

1. menu **Status > Target health** (sur les anciennes versions : **Status > Targets**) ;
2. tapez `croustino` dans la recherche ;
3. vous devez voir le groupe **`serviceMonitor/croustino/back/0`** avec **2 cibles `UP`**, une par pod du back (`http://<IP du pod>:8080/metrics`).

Prometheus peut mettre jusqu'à 30 secondes à prendre en compte le ServiceMonitor : rafraîchissez la page.

> Pas de groupe `croustino` ? `kubectl get servicemonitor -n croustino` : s'il n'existe pas, le monitoring n'est pas activé dans la release. S'il existe sans cible, son `selector` ne trouve pas le Service : vérifiez le label `app: back` et le nom de port `http` (`kubectl get svc back -n croustino -o yaml`). Des cibles `DOWN` : lisez l'erreur affichée à côté.

### 3. Simuler le rush et écrire du PromQL

#### 3.1 Lancer le rush

```bash
kubectl delete job rush-du-matin -n croustino --ignore-not-found
kubectl apply -f k8s/charge/rush-du-matin.yaml
kubectl get pods -n croustino -l job-name=rush-du-matin
```

Trois clients passent chacun 600 commandes, une toutes les 0,2 s : le rush dure **environ 2 minutes**. Les quantités vont de 1 à 30 et la fournée est limitée à 24 : environ **20 % des commandes sont rejetées**. Relancez ces commandes chaque fois que vous voulez de nouvelles données.

#### 3.2 Où écrire les requêtes

Dans le navigateur de ClientWeb, sur Prometheus (`http://10.10.0.11:30090`) :

1. menu **Query** (sur les anciennes versions : **Graph**) ;
2. écrivez la requête dans le champ de saisie, puis cliquez sur **Execute** ;
3. onglet **Table** : la valeur actuelle, une ligne par série ;
4. onglet **Graph** : l'évolution dans le temps. Réglez la durée sur **15m** pour bien voir le rush.

#### 3.3 Requête 1 : commandes enregistrées par minute, par produit

Construisez-la morceau par morceau, en regardant le résultat à chaque fois.

**a.** Le compteur brut, onglet **Table** :

```promql
croustino_commandes_total
```

Une ligne par produit **et par pod du back** (regardez les labels `produit` et `pod`). La valeur est le nombre total de commandes depuis le démarrage du pod : un compteur ne fait que monter.

**b.** La vitesse, onglet **Graph** :

```promql
rate(croustino_commandes_total[1m])
```

`rate(…[1m])` calcule combien le compteur augmente **par seconde**, en moyenne sur la dernière minute. Le rush apparaît comme une bosse.

**c.** Additionner les deux pods du back, en gardant le produit :

```promql
sum by (produit) (rate(croustino_commandes_total[1m]))
```

**d.** Passer en commandes par minute :

```promql
sum by (produit) (rate(croustino_commandes_total[1m])) * 60
```

**Résultat attendu pendant le rush :** 4 courbes (une par produit), autour de **180 commandes par minute** chacune.

#### 3.4 Requête 2 : taux de rejet

Les rejets par seconde, puis les commandes enregistrées par seconde :

```promql
sum(rate(croustino_commandes_rejetees_total[5m]))
```

```promql
sum(rate(croustino_commandes_total[5m]))
```

Le taux de rejet en %, c'est rejets / (rejets + enregistrées) × 100 :

```promql
sum(rate(croustino_commandes_rejetees_total[5m]))
/
(sum(rate(croustino_commandes_rejetees_total[5m])) + sum(rate(croustino_commandes_total[5m])))
* 100
```

**Résultat attendu :** environ **20**.

#### 3.5 Requête 3 : mémoire de chaque pod de Croustino

Les métriques des conteneurs viennent du kubelet. On filtre sur le namespace avec `{…}`, et on écarte la ligne de total du pod (`container=""`) :

```promql
container_memory_working_set_bytes{namespace="croustino", container!=""}
```

Puis une ligne par pod, en Mio :

```promql
sum by (pod) (container_memory_working_set_bytes{namespace="croustino", container!=""}) / 1024 / 1024
```

**Résultat attendu :** de l'ordre de 30 à 50 Mio pour le back et PostgreSQL, quelques Mio pour le front.

#### 3.6 Requête 4 : redémarrages des conteneurs de Croustino

Cette métrique vient de kube-state-metrics, qui expose l'état des objets Kubernetes :

```promql
kube_pod_container_status_restarts_total{namespace="croustino"}
```

Une ligne par conteneur : la valeur est le nombre total de redémarrages. Les redémarrages de la dernière heure, par pod :

```promql
sum by (pod) (increase(kube_pod_container_status_restarts_total{namespace="croustino"}[1h]))
```

> Si l'incident du TP 05 date de moins d'une heure, vous retrouvez ici ses traces.

**À retenir :** `{…}` filtre sur les labels, `rate()` transforme un compteur en vitesse, `sum by (…)` regroupe. Gardez ces requêtes : elles servent au dashboard de l'étape suivante.

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
