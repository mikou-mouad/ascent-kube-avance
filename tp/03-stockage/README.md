# TP 03 – « Les commandes du matin ont disparu »

**Durée :** 55 min · **Branche :** `tp-03-stockage` · **Correction :** branche `tp-04-rbac` (`k8s/10-postgres.yaml`)

## L'incident

> Mardi, 8h05. Le nœud qui héberge PostgreSQL redémarre après une mise à jour de sécurité.
> Kubernetes recrée le pod ailleurs en quelques secondes. Bravo… sauf que la base est vide : 212 commandes du matin ont disparu.
> Les livreurs partent sans savoir où aller.

## Objectifs

- Comprendre pourquoi les données d'un conteneur sont éphémères.
- Installer un provisionneur dynamique et une StorageClass par défaut.
- Comprendre le cycle PVC → PV et le mode `WaitForFirstConsumer`.
- Migrer PostgreSQL vers un StatefulSet avec `volumeClaimTemplates`.

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-03-stockage
```

La branche contient l'état attendu à la fin du TP précédent (c'est aussi sa correction).
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Étapes

`k8s/` contient la correction du TP 02. Appliquez-la pour partir d'un état propre :

```bash
kubectl apply -f k8s/
```

### 1. Reproduire l'incident

1. Passez 2 ou 3 commandes depuis le site.
2. Supprimez le pod PostgreSQL : `kubectl delete pod -l app=postgres`.
3. Rafraîchissez le site au bout de 10 secondes. Où sont passées les commandes ?

### 2. Installer un provisionneur de volumes

Le cluster n'a aucune StorageClass :

```bash
kubectl get storageclass
```

Installez local-path-provisioner (il crée les volumes dans un dossier du nœud) et déclarez-le par défaut :

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
kubectl patch storageclass local-path \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
kubectl get storageclass
```

**Questions :** quel est le `reclaimPolicy` de cette StorageClass ? Que signifie `volumeBindingMode: WaitForFirstConsumer` ?

### 3. Observer le provisionnement dynamique

Créez un PVC de test (`test-pvc.yaml`, 100Mi, sans `storageClassName`) puis :

```bash
kubectl get pvc test-pvc          # Pending : pourquoi ?
kubectl run conso --image=busybox --restart=Never \
  --overrides='{"spec":{"volumes":[{"name":"v","persistentVolumeClaim":{"claimName":"test-pvc"}}],"containers":[{"name":"conso","image":"busybox","command":["sleep","3600"],"volumeMounts":[{"name":"v","mountPath":"/data"}]}]}}'
kubectl get pvc,pv                # Bound
kubectl get pod conso -o wide     # sur quel nœud ?
```

Supprimez le pod puis le PVC. Que devient le PV ?

### 4. Migrer PostgreSQL en StatefulSet

Réécrivez `k8s/10-postgres.yaml` :

- un **Service headless** `postgres` (`clusterIP: None`) ;
- un **StatefulSet** `postgres` avec `serviceName: postgres`, 1 réplica, le même conteneur qu'avant ;
- un `volumeClaimTemplates` nommé `data` de 1Gi, monté sur `/var/lib/postgresql/data`.

Le Service s'appelle toujours `postgres` : le back n'a pas besoin d'être modifié.

```bash
kubectl delete deployment postgres
kubectl delete service postgres     # on ne peut pas passer un Service existant en headless
kubectl apply -f k8s/10-postgres.yaml
kubectl get statefulset,pod,pvc
```

### 5. Vérifier que l'incident est résolu

1. Passez des commandes.
2. Supprimez le pod `postgres-0`.
3. Vérifiez que le nouveau pod porte le **même nom**, réutilise le **même PVC**, et que les commandes sont toujours là.
4. Retrouvez le dossier des données sur le nœud (`kubectl get pv -o yaml`, champ `hostPath` / `local.path`).

## Questions de fin

1. Pourquoi un StatefulSet plutôt qu'un Deployment avec un PVC ?
2. Que se passe-t-il pour les données si on supprime le StatefulSet ? Et si on supprime le PVC ?
3. Avec local-path, que se passe-t-il si le nœud qui porte le volume tombe définitivement ? Quelle solution en production ?

## Bonus

- Passez le StatefulSet à 2 réplicas : quels noms de pods et de PVC obtenez-vous ? Les deux bases sont-elles synchronisées ? Revenez à 1.
- Résolvez `postgres-0.postgres.croustino.svc.cluster.local` depuis un pod busybox (`nslookup`).
- Créez une StorageClass `local-path-retain` avec `reclaimPolicy: Retain` et testez la suppression d'un PVC.
