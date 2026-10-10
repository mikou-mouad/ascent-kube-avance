# TP 05 – « Le service promos a mangé toute la RAM »

**Durée :** 50 min · **Branche :** `tp-05-capacite` · **Correction :** `solutions/05-capacite/`, dans cette branche

## L'incident

> Vendredi, 7h02. Un prestataire a déployé le nouveau service « promos » dans le namespace `croustino`.
> Il consomme 1,5 Go par pod, sans aucune limite. Les nœuds saturent, le noyau tue des processus au hasard : le back redémarre en boucle en plein rush.

## Objectifs

- Comprendre `allocatable`, requests, limits et classes QoS.
- Mesurer la consommation réelle avec metrics-server.
- Imposer des valeurs par défaut et des maximums avec LimitRange.
- Plafonner la consommation d'un namespace avec ResourceQuota.

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-05-capacite
```

La branche contient l'état attendu à la fin du TP précédent. La correction de ce TP est dans `solutions/05-capacite/`.
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Étapes

### 1. Capacité du cluster

```bash
kubectl describe node worker1 | grep -A 8 -E "Capacity|Allocatable|Allocated resources"
kubectl get pods -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass
```

**Question :** quelle est la classe QoS des pods de Croustino ? Pourquoi est-ce risqué ?

### 2. Installer metrics-server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
# Sur kubeadm, les certificats des kubelets ne sont pas signés pour leur IP :
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment metrics-server
kubectl top nodes
kubectl top pods -n croustino
```

### 3. Rejouer l'incident

Le service `promos` réserve et consomme presque toute la mémoire libre de chaque worker. Le script calcule la taille selon vos nœuds :

```bash
chmod +x k8s/capacite/lancer-promos.sh
k8s/capacite/lancer-promos.sh
```

Dans un second terminal, suivez les pods, et gardez le site ouvert sur ClientWeb :

```bash
kubectl get pods -n croustino -o wide -w
```

`promos` remplit la mémoire en une à trois minutes (`kubectl top pods -n croustino` montre sa consommation monter). Vous devez ensuite observer :

- les pods `promos` qui tournent, un par worker, sans jamais redémarrer ;
- les pods de Croustino (back, front, PostgreSQL) en `Evicted`, `OOMKilled`, `Pending` ou `CrashLoopBackOff` : **le site tombe** ;
- la condition `MemoryPressure` à `True` : `kubectl describe node worker1 | grep -A 8 Conditions` ;
- les événements : `kubectl get events -n croustino --sort-by=.lastTimestamp | tail -20`.

Comparez les classes QoS :

```bash
kubectl get pods -n croustino -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass,ETAT:.status.phase
```

**Question :** pourquoi est-ce Croustino qui tombe, alors que c'est `promos` qui consomme la mémoire ?

Arrêtez `promos` et nettoyez les pods évincés :

```bash
kubectl delete deployment promos -n croustino
kubectl delete pods -n croustino --field-selector=status.phase=Failed
kubectl get pods -n croustino -w      # attendre que tout redevienne Running
```

### 4. Des valeurs par défaut avec LimitRange

Créez `k8s/capacite/limitrange.yaml` dans `croustino` :

- par conteneur : request par défaut `100m` CPU / `128Mi`, limit par défaut `500m` / `256Mi` ;
- maximum par conteneur : `1` CPU / `1Gi`.

Appliquez-le puis relancez `k8s/capacite/lancer-promos.sh`. Que se passe-t-il ? (`kubectl get pods -n croustino`, `kubectl describe rs -n croustino -l app=promos`, `kubectl get events -n croustino`)

Supprimez ensuite le Deployment `promos`.

> Un LimitRange ne s'applique qu'aux pods **créés après** lui : faites un `kubectl rollout restart` des Deployments existants et vérifiez leurs ressources.

### 5. Un plafond pour le namespace avec ResourceQuota

Créez `k8s/capacite/quota.yaml` :

| Ressource | Plafond |
|-----------|---------|
| `requests.cpu` | 2 |
| `requests.memory` | 2Gi |
| `limits.cpu` | 4 |
| `limits.memory` | 4Gi |
| `pods` | 15 |
| `persistentvolumeclaims` | 3 |

```bash
kubectl describe resourcequota -n croustino
kubectl scale deployment front --replicas=20
kubectl get deployment front
kubectl get events --sort-by=.lastTimestamp | tail
kubectl scale deployment front --replicas=2
```

### 6. Des ressources explicites pour Croustino

Ne laissez pas les valeurs par défaut décider : ajoutez `resources` dans `k8s/10-postgres.yaml`, `k8s/20-back.yaml` et `k8s/30-front.yaml`, à partir de ce que montre `kubectl top`.
Donnez à PostgreSQL la classe QoS **Guaranteed**. Vérifiez avec `kubectl get pods -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass`.

## Questions de fin

1. Différence entre dépasser sa limite CPU et dépasser sa limite mémoire ?
2. Sur quoi se base le scheduler pour placer un pod : requests, limits ou consommation réelle ?
3. Dans quel ordre le kubelet évince-t-il les pods quand un nœud manque de mémoire ?

## Bonus

- Ajoutez un `HorizontalPodAutoscaler` sur le back (CPU 70 %, 2 à 5 réplicas) et chargez-le avec une boucle `curl`.
- Créez une `PriorityClass` haute pour le back et PostgreSQL : que se passe-t-il quand le cluster est plein ?
