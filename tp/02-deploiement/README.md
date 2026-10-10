# TP 02 – Première migration de Croustino

**Durée :** 1 h 45 · **Branche :** `tp-02-deploiement` · **Correction :** `solutions/02-deploiement/`, dans cette branche

## L'incident

> Le cluster est prêt. Sophie veut voir Croustino tourner dessus avant la fin de la journée.
> Malik n'a jamais écrit de YAML Kubernetes. Inès propose de migrer composant par composant : la base, puis l'API, puis le front.

## Objectifs

- Créer un namespace, un Secret et une ConfigMap.
- Écrire des Deployments et des Services, comprendre labels et sélecteurs.
- Exposer une application avec un NodePort.
- Utiliser les probes, le scaling, l'auto-réparation et le rolling update.

## Ce qu'on migre

Regardez `app/docker-compose.yml` : c'est l'application telle qu'elle tourne sur la VM.

| Composant | Image | Port | Configuration |
|-----------|-------|------|---------------|
| postgres  | `postgres:16` | 5432 | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| back      | `ghcr.io/mikou-mouad/croustino-back:1.0` | 8080 | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `VILLE`, `STOCK_MAX` |
| front     | `ghcr.io/mikou-mouad/croustino-front:1.0` | 80 | appelle le back sur `http://back:8080` |

Routes utiles du back : `/healthz` (vivant), `/readyz` (base joignable), `/api/produits`, `/api/commandes`, `/api/version`.

## Avant de commencer : récupérer les fichiers

Sur le **control plane**, installez git et clonez le dépôt de la formation :

```bash
sudo apt-get install -y git
git clone https://github.com/mikou-mouad/ascent-kube-avance.git ~/croustino
cd ~/croustino
git checkout tp-02-deploiement
```

Toutes les commandes des TP se lancent ensuite depuis `~/croustino`.

## Étapes

Toutes les commandes se lancent sur le control plane, depuis le dossier du dépôt (`~/croustino`).

### 1. Namespace

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl config set-context --current --namespace=croustino
```

### 2. Secret et ConfigMap

Générez les manifests avec `kubectl` plutôt que de les écrire à la main :

```bash
kubectl create secret generic croustino-db \
  --from-literal=POSTGRES_USER=croustino \
  --from-literal=POSTGRES_PASSWORD=croissant-chaud \
  --dry-run=client -o yaml > k8s/01-secret.yaml

kubectl create configmap back-config \
  --from-literal=DB_HOST=postgres \
  --from-literal=DB_NAME=croustino \
  --from-literal=VILLE=Rennes \
  --from-literal=STOCK_MAX=24 \
  --dry-run=client -o yaml > k8s/02-configmap.yaml
```

Ajoutez `namespace: croustino` dans les deux fichiers, puis appliquez-les.

**Question :** décodez le mot de passe stocké dans le Secret (`kubectl get secret croustino-db -o yaml`, puis `base64 -d`). Un Secret est-il chiffré ?

### 3. PostgreSQL

`k8s/10-postgres.yaml` est fourni complet. Lisez-le, puis appliquez-le.

```bash
kubectl apply -f k8s/10-postgres.yaml
kubectl get pods -w
kubectl exec -it deploy/postgres -- psql -U croustino -c '\l'
```

**Questions :** comment le pod reçoit-il le mot de passe ? À quoi sert la `readinessProbe` ?

### 4. Le back

Complétez les `TODO` de `k8s/20-back.yaml`, puis :

```bash
kubectl apply -f k8s/20-back.yaml
kubectl get pods -l app=back
kubectl logs -l app=back --tail=5
kubectl get endpointslices -l kubernetes.io/service-name=back
```

Testez l'API depuis le cluster :

```bash
kubectl run test --rm -it --image=curlimages/curl --restart=Never -- \
  curl -s http://back:8080/api/produits
```

### 5. Le front

Complétez les `TODO` de `k8s/30-front.yaml` et appliquez-le.

Le Service est de type **NodePort** : le site répond sur le port `30080` de **chaque nœud** du cluster. Pour trouver l'adresse des nœuds :

```bash
kubectl get nodes -o wide      # colonne INTERNAL-IP
```

| Nœud | INTERNAL-IP |
|------|-------------|
| controlplane | 10.10.0.10 |
| worker1 | 10.10.0.11 |
| worker2 | 10.10.0.12 |

Pour voir le site, utilisez la machine **ClientWeb** (`10.10.0.50`), sur le même réseau que les nœuds :

1. Dans votre environnement de TP, cliquez sur **Ouvrir la console** de ClientWeb.
2. Ouvrez un navigateur web sur ce bureau.
3. Allez sur `http://10.10.0.11:30080` (l'adresse de n'importe quel nœud fonctionne).
4. Passez une commande.

C'est aussi depuis ClientWeb que vous ouvrirez Grafana, Kibana et Harbor dans les TP suivants : partout où un énoncé écrit `<IP d'un nœud>`, utilisez l'une de ces adresses.

**Question :** pourquoi le site répond-il aussi sur `10.10.0.10`, alors qu'aucun pod du front ne tourne sur le control plane ?

### 6. Scaling et auto-réparation

```bash
kubectl scale deployment back --replicas=3
kubectl get pods -o wide
```

Rafraîchissez la page : le bandeau indique quel pod du back a répondu.
Supprimez un pod du back (`kubectl delete pod <nom>`) et observez ce que fait le Deployment.

### 7. Rolling update sans coupure

Malik livre la version 1.1 du front (bandeau vert). Vérifiez d'abord que le front tourne en **1.0** (bandeau marron) :

```bash
kubectl get deployment front -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

Puis passez en 1.1 :

```bash
kubectl set image deployment/front front=ghcr.io/mikou-mouad/croustino-front:1.1
kubectl rollout status deployment/front
kubectl rollout history deployment/front      # 2 révisions
```

Gardez la page ouverte pendant la mise à jour : le site reste disponible.
Revenez en arrière avec `kubectl rollout undo deployment/front`, puis remettez la 1.1.

> `rollout history` n'affiche qu'une révision et `undo` répond « no rollout history found » ? L'image était déjà en 1.1 : `set image` n'a rien changé. Repassez en 1.0 avec `kubectl set image`, puis recommencez cette étape.

## Questions de fin

1. Que se passe-t-il si le sélecteur d'un Service ne correspond à aucun pod ?
2. Pourquoi le back n'apparaît-il dans les endpoints qu'une fois la base prête ?
3. Comparez avec la VM : qu'a-t-on gagné ? Que manque-t-il encore ?

## Bonus

- Passez PostgreSQL à 0 réplica : que deviennent les pods du back et les endpoints ? Remettez-le à 1.
- Ajoutez une `strategy` au Deployment du front (`maxSurge: 1`, `maxUnavailable: 0`) et expliquez la différence.
- Annotez le changement de version : `kubectl annotate deployment/front kubernetes.io/change-cause="front 1.1"`.
