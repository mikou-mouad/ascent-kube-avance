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

Un **ServiceMonitor** dit à Prometheus quoi collecter : quel Service (par ses labels), sur quel port, à quel chemin et à quelle fréquence. On l'ajoute au chart, dans un nouveau fichier `helm/croustino/templates/monitoring.yaml`, activable par une value, car Lyon n'aura peut-être pas de monitoring.

1. Dans `helm/croustino/values.yaml`, ajoutez :

   ```yaml
   # ServiceMonitor, alertes et dashboard (nécessite kube-prometheus-stack)
   monitoring:
     enabled: false
   ```

2. Créez `helm/croustino/templates/monitoring.yaml` :

   ```yaml
   {{- if .Values.monitoring.enabled }}
   # Prometheus collecte /metrics sur le Service du back.
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: back
   spec:
     selector:
       matchLabels:
         app: back          # le label du Service back
     endpoints:
       - port: http         # le NOM du port du Service, pas son numéro
         path: /metrics
         interval: 15s
   {{- end }}
   ```

   Tout le fichier est entre `{{- if .Values.monitoring.enabled }}` et `{{- end }}` : sans `monitoring.enabled=true`, Helm ne génère rien. Les étapes 4 et 5 ajouteront d'autres objets **avant** la ligne `{{- end }}`.

3. Vérifiez le rendu, puis déployez :

   ```bash
   helm template croustino helm/croustino --set monitoring.enabled=true -s templates/monitoring.yaml
   helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml --set monitoring.enabled=true
   kubectl get servicemonitor -n croustino
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

Grafana affiche les requêtes de Prometheus sous forme de tableaux de bord. On y construit 4 panneaux à partir des requêtes de l'étape 3.

#### 4.1 Se connecter

Dans le navigateur de ClientWeb : `http://10.10.0.11:30300`, utilisateur `admin`, mot de passe `croustino`.

#### 4.2 Créer le dashboard et le premier panneau

Les noms de boutons ci-dessous sont ceux de Grafana 12, installé par le chart.

1. Menu ☰ (en haut à gauche) > **Dashboards**, puis bouton **New** > **New dashboard**.
2. Un volet **Add** s'ouvre à droite. Laissez la disposition **Custom grid** et cliquez sur la vignette **Panel** (« Drag or click to add a panel »).
3. Un panneau « New panel » apparaît : cliquez sur **Configure visualization**. Si Grafana demande une source de données, choisissez **Prometheus**.
4. Dans l'éditeur de requête (en bas), passez de **Builder** à **Code** (sélecteur à droite de l'éditeur), puis collez :

   ```promql
   sum by (produit) (rate(croustino_commandes_total[1m])) * 60
   ```

5. Sous la requête, ouvrez **Options** et mettez `{{produit}}` dans **Legend** (choisir **Custom**) : chaque courbe porte le nom du produit.
6. Cliquez sur **Run queries**.
7. Dans le panneau de droite :
   - le type de visualisation est affiché tout en haut : **Time series** par défaut (le lien **Change** à côté permet d'en choisir un autre) ;
   - **Panel options > Title** : `Commandes par minute`.
8. En haut à droite, cliquez sur **Back** pour revenir au dashboard. Inutile d'enregistrer à chaque panneau : vos modifications sont conservées tant que vous ne cliquez pas sur **Discard**. On enregistre tout à l'étape 4.4.

#### 4.3 Les trois autres panneaux

Pour chaque panneau : bouton **+** en haut à gauche du dashboard, vignette **Panel**, **Configure visualization**, puis requête en mode **Code**, **Run queries**, réglages à droite (type de visualisation avec **Change**), **Back**.

| Title | Requête (mode Code) | Visualization | Legend | Standard options |
|-------|---------------------|---------------|--------|------------------|
| `Taux de rejet` | `sum(rate(croustino_commandes_rejetees_total[5m])) / (sum(rate(croustino_commandes_rejetees_total[5m])) + sum(rate(croustino_commandes_total[5m]))) * 100` | Stat | – | Unit : `Percent (0-100)` |
| `Mémoire par pod` | `sum by (pod) (container_memory_working_set_bytes{namespace="croustino", container!=""})` | Time series | `{{pod}}` | Unit : `bytes(IEC)` |
| `Redémarrages (1 h)` | `sum(increase(kube_pod_container_status_restarts_total{namespace="croustino"}[1h]))` | Stat | – | Decimals : `0` |

**Trouver une option** (Unit, Decimals…) : cliquez sur la **loupe** en haut du volet de droite et tapez son nom, par exemple `unit`. Pour l'unité, ne parcourez pas les catégories : tapez directement dans le champ **Unit** (`percent` ou `bytes`), puis choisissez **Percent (0-100)** ou **bytes(IEC)** dans la liste filtrée.

**Contrôle :** « Taux de rejet » et « Redémarrages (1 h) » doivent afficher **une seule valeur**. Une case par pod veut dire que la requête n'est pas la bonne : il manque le `sum(…)` qui additionne tout.

Vous pouvez déplacer et redimensionner les panneaux à la souris.

#### 4.4 Régler et enregistrer

1. En haut à droite, cliquez sur la période (**Last 6 hours** par défaut) et choisissez **Last 15 minutes**. Avec la flèche à droite du bouton **Refresh**, choisissez un rafraîchissement automatique de **10s**.
2. Cliquez sur le bouton bleu **Save** en haut à droite, titre : `Croustino Rennes – Rush du matin`, puis **Save**.
3. Relancez le rush et regardez le dashboard se remplir.

   ```bash
   kubectl delete job rush-du-matin -n croustino --ignore-not-found
   kubectl apply -f k8s/charge/rush-du-matin.yaml
   ```

Explorez aussi un dashboard fourni par la stack : **Dashboards**, recherchez `Compute Resources / Namespace (Pods)`, puis choisissez `croustino` dans la liste **namespace** en haut.

#### 4.5 Livrer le dashboard avec le chart

Un dashboard créé à la main disparaît si Grafana est réinstallé. On le range donc dans le chart, comme le reste de l'application : Grafana charge automatiquement les ConfigMaps qui portent le label `grafana_dashboard: "1"`.

1. Dans l'adresse du dashboard (`…/d/abc123xyz/croustino-rennes…`), relevez son **uid** : la partie entre `/d/` et le `/` suivant.
2. Sur le control plane, récupérez son JSON avec l'API de Grafana. On remplace l'`id` et l'`uid` pour que la copie livrée par le chart ne remplace pas votre original :

   ```bash
   sudo apt-get install -y jq
   UID_DASH=abc123xyz        # votre uid
   mkdir -p helm/croustino/dashboards
   curl -s -u admin:croustino http://10.10.0.10:30300/api/dashboards/uid/$UID_DASH \
     | jq '.dashboard | .id = null | .uid = "croustino-chart" | .title = "Croustino Rennes (livré par le chart)"' \
     > helm/croustino/dashboards/rush-du-matin.json
   head -5 helm/croustino/dashboards/rush-du-matin.json
   ```

3. Ajoutez à la fin de `helm/croustino/templates/monitoring.yaml`, **avant** la dernière ligne `{{- end }}` :

   ```yaml
   ---
   # Dashboard chargé automatiquement par Grafana (label grafana_dashboard)
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: dashboard-croustino
     labels:
       grafana_dashboard: "1"
   data:
     rush-du-matin.json: |-
   {{ .Files.Get "dashboards/rush-du-matin.json" | indent 4 }}
   ```

   `.Files.Get` lit un fichier du chart : le JSON est copié dans la ConfigMap au moment du `helm upgrade`.

4. Déployez et vérifiez :

   ```bash
   helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml --set monitoring.enabled=true
   kubectl get configmap dashboard-croustino -n croustino --show-labels
   ```

5. Dans Grafana, **Dashboards** : le dashboard « Croustino Rennes (livré par le chart) » apparaît en moins d'une minute.

### 5. L'alerte

Le dashboard montre le problème… à condition que quelqu'un le regarde. Une **alerte** prévient toute seule. Elle est décrite dans un objet **PrometheusRule** :

- `expr` : une requête PromQL ; l'alerte se déclenche quand elle renvoie un résultat ;
- `for` : combien de temps la condition doit rester vraie avant de déclencher (pour éviter les fausses alertes) ;
- `labels` : par exemple la gravité (`severity`) ;
- `annotations` : le texte du message.

#### 5.1 Tester la condition dans Prometheus

On quitte Grafana : les alertes se définissent et se suivent dans **Prometheus**. Dans le navigateur de ClientWeb, ouvrez un nouvel onglet sur **http://10.10.0.11:30090/query** (page **Query** de Prometheus) et, pendant un rush, exécutez :

```promql
sum(increase(croustino_commandes_rejetees_total{namespace="croustino"}[5m]))
```

`increase(…[5m])` donne le nombre de commandes rejetées sur les 5 dernières minutes. Pendant le rush, vous devez voir plusieurs centaines. On alertera **au-delà de 10**.

#### 5.2 Ajouter la règle au chart

Ajoutez à `helm/croustino/templates/monitoring.yaml`, **avant** la dernière ligne `{{- end }}` :

```yaml
---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: croustino
spec:
  groups:
    - name: croustino
      rules:
        - alert: CroustinoRejetsEleves
          expr: sum(increase(croustino_commandes_rejetees_total{namespace="{{ .Release.Namespace }}"}[5m])) > 10
          for: 1m
          labels:
            severity: warning
          annotations:
            summary: "Croustino : plus de 10 commandes rejetées en 5 minutes"
```

`{{ .Release.Namespace }}` est remplacé par Helm : la même règle fonctionnera pour Lyon.

```bash
helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml --set monitoring.enabled=true
kubectl get prometheusrule -n croustino
```

Dans Prometheus, ouvrez **http://10.10.0.11:30090/rules** (menu **Status > Rule health**) : le groupe `croustino` apparaît, avec la règle `CroustinoRejetsEleves` marquée **OK**. Attention : `OK` indique que la règle s'évalue sans erreur, pas l'état de l'alerte. L'état (Inactive, Pending, Firing) se suit sur la page **Alerts**, à l'étape suivante.

#### 5.3 Déclencher l'alerte

1. Relancez le rush.

   ```bash
   kubectl delete job rush-du-matin -n croustino --ignore-not-found
   kubectl apply -f k8s/charge/rush-du-matin.yaml
   ```
2. Dans Prometheus, ouvrez **http://10.10.0.11:30090/alerts** (menu **Alerts**) et suivez l'état de `CroustinoRejetsEleves`, en rafraîchissant la page (si seules les alertes actives sont affichées, utilisez le filtre d'état en haut de la page pour voir aussi les inactives) :

| État | Signification | Quand |
|------|---------------|-------|
| **Inactive** | la condition est fausse | avant le rush |
| **Pending** | la condition est vraie, Prometheus attend la durée `for` | quelques secondes après le début du rush |
| **Firing** | la condition est vraie depuis 1 minute : l'alerte est envoyée | environ 1 min 30 après le début du rush |

3. Ouvrez Alertmanager dans un autre onglet : **http://10.10.0.11:30093**. L'alerte y apparaît avec son label `severity="warning"`. C'est Alertmanager qui enverrait le mail, le message Slack ou le SMS (aucun destinataire n'est configuré ici).
4. Environ 5 minutes après la fin du rush, `increase(…[5m])` redescend sous 10 : l'alerte repasse en **Inactive** et disparaît d'Alertmanager.

> L'alerte n'apparaît pas dans **Status > Rule health** ? Vérifiez `kubectl get prometheusrule -n croustino`, puis que le `helm upgrade` contient bien `--set monitoring.enabled=true`.

## Questions de fin

1. Pourquoi Prometheus « tire » les métriques (pull) au lieu de les recevoir ?
2. Pourquoi utiliser `rate()` sur un compteur plutôt que sa valeur brute ?
3. Quelles autres alertes Croustino devrait-il avoir ?

## Bonus

- Ajoutez une alerte `CroustinoBackRedemarre` sur les redémarrages du back et provoquez-la (`kubectl exec deploy/back -- sh -c 'kill 1'`).
- Envoyez les alertes vers un webhook de test (configuration d'Alertmanager).
- Activez le monitoring pour Lyon et filtrez le dashboard par namespace avec une variable.
