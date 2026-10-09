# TP 08 – « La commande perdue »

**Durée :** 55 min · **Branche :** `tp-08-logs` · **Correction :** branche `tp-09-audit` (`solutions/08-logs.md`)

## L'incident

> Mercredi, 9h30. Mme Lebrun appelle, furieuse : elle a commandé des croissants pour la réunion de 8h, rien n'est arrivé.
> Malik veut lire les logs du back… mais les pods ont été remplacés par le déploiement de 8h15. `kubectl logs` ne montre plus rien.
> Les logs vivent et meurent avec les pods.

## Objectifs

- Comprendre où sont écrits les logs des conteneurs et pourquoi ils disparaissent.
- Déployer une chaîne EFK : Elasticsearch, Fluent Bit, Kibana.
- Exploiter des logs structurés (JSON) et les métadonnées Kubernetes.
- Retrouver un événement après la disparition du pod.

## Étapes

### 1. Où sont les logs ?

Sur un worker :

```bash
sudo ls /var/log/containers/ | grep croustino
sudo ls /var/log/pods/
```

`kubectl logs deploy/back -n croustino --tail=3` : quel format ont les logs du back ?

### 2. Installer Elasticsearch et Kibana (opérateur ECK)

Vérifiez d'abord la mémoire disponible (`kubectl top nodes`) : Elasticsearch demande 2 Go.

```bash
kubectl create -f https://download.elastic.co/downloads/eck/2.16.1/crds.yaml
kubectl apply -f https://download.elastic.co/downloads/eck/2.16.1/operator.yaml
kubectl create namespace logging
kubectl apply -f k8s/logs/elasticsearch-kibana.yaml
kubectl get elasticsearch,kibana -n logging -w      # attendre HEALTH green/yellow
```

**Questions :** quels objets l'opérateur a-t-il créés (`kubectl get all,secret,pvc -n logging`) ? Où est stocké le mot de passe de `elastic` ?

### 3. Installer Fluent Bit

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm install fluent-bit fluent/fluent-bit -n logging -f k8s/logs/values-fluent-bit.yaml
kubectl get pods -n logging -o wide -l app.kubernetes.io/name=fluent-bit
kubectl logs -n logging -l app.kubernetes.io/name=fluent-bit --tail=20
```

**Question :** pourquoi un DaemonSet ? Pourquoi n'y a-t-il pas de pod Fluent Bit sur le control plane ?

### 4. Rejouer l'incident

Mme Lebrun passe sa commande :

```bash
kubectl run lebrun --rm -it --image=curlimages/curl --restart=Never -n croustino -- \
  curl -s -X POST http://back:8080/api/commandes -H 'Content-Type: application/json' \
  -d '{"client":"Mme Lebrun","produit":"croissant","quantite":30}'
```

Puis le déploiement de 8h15 remplace les pods :

```bash
kubectl rollout restart deployment back -n croustino
kubectl rollout status deployment back -n croustino
kubectl logs deploy/back -n croustino | grep Lebrun     # plus rien
```

### 5. Enquêter dans Kibana

```bash
kubectl get secret logs-es-elastic-user -n logging -o go-template='{{.data.elastic | base64decode}}'; echo
```

Ouvrez `https://<IP d'un nœud>:30561` (certificat auto-signé, utilisateur `elastic`).

1. **Stack Management > Data Views** : créez la vue `kube-*` (champ de temps `@timestamp`).
2. **Discover** : retrouvez la commande de Mme Lebrun avec une requête KQL.
3. Répondez : quel est le numéro de commande ? Quel pod l'a traitée ? Pourquoi a-t-elle été rejetée ?

Indices KQL : `kubernetes.namespace_name : "croustino"`, `client : "Mme Lebrun"`, `niveau : "ERROR"`.

### 6. Pour Sophie

Lancez le rush (`kubectl delete job rush-du-matin -n croustino --ignore-not-found; kubectl apply -f k8s/charge/rush-du-matin.yaml`).
Dans Discover, affichez uniquement les colonnes `commande_id`, `client`, `quantite`, `raison` pour les rejets, et sauvegardez la recherche « Commandes rejetées ».

## Questions de fin

1. Pourquoi des logs JSON plutôt que du texte libre ?
2. Que deviennent les logs si Elasticsearch est indisponible pendant 10 minutes ?
3. Comment limiter la durée de conservation et l'espace disque des logs ?

## Bonus

- Construisez une visualisation Lens : nombre de rejets par produit.
- Ajoutez une tolérance au DaemonSet pour collecter aussi les logs du control plane.
- Comparez avec Loki + Grafana, déjà présent depuis le TP 07 : avantages et limites.
