# TP 11 – « Le control plane est tombé la veille de l'Épiphanie »

**Durée :** 1 h 05 · **Branche :** `tp-11-cycle-de-vie` · **Correction :** branche `solution-finale` (`helm/croustino/templates/pdb.yaml`, `solutions/11-cycle-de-vie.md`)

## L'incident

> 5 janvier, 22h. Veille de l'Épiphanie : Croustino attend 4 000 galettes en commande.
> Malik lance un script de nettoyage qui supprime le namespace `croustino-lyon` au lieu de `croustino-lyon-test`.
> Inès découvre aussi que la version de Kubernetes ne reçoit bientôt plus de correctifs. Il faut la mettre à jour… sans couper le site.

## Objectifs

- Protéger l'application pendant les maintenances avec des PodDisruptionBudgets.
- Sauvegarder et restaurer etcd.
- Mettre à jour un cluster kubeadm d'une version mineure, nœud par nœud.
- Identifier les points faibles de l'architecture (single points of failure).

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-11-cycle-de-vie
```

La branche contient l'état attendu à la fin du TP précédent (c'est aussi sa correction).
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Étapes

### 1. PodDisruptionBudgets (10 min)

Ajoutez au chart un template `pdb.yaml` : un PodDisruptionBudget pour le back et un pour le front, avec `maxUnavailable: 1`, **uniquement si le Deployment a plus d'un réplica**.

```bash
helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml
kubectl get pdb -n croustino
```

**Question :** pourquoi ne pas créer de PDB quand il n'y a qu'un réplica ?

### 2. Sauvegarder etcd (10 min)

```bash
kubectl -n kube-system exec etcd-controlplane -- etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /var/lib/etcd/sauvegarde-tp11.db

sudo ls -lh /var/lib/etcd/
kubectl -n kube-system exec etcd-controlplane -- etcdutl snapshot status /var/lib/etcd/sauvegarde-tp11.db -w table
```

**Question :** la sauvegarde est sur le disque du control plane. Est-ce suffisant ?

### 3. L'accident, puis la restauration (15 min)

```bash
kubectl delete namespace croustino-lyon
kubectl get ns
```

Restaurez la sauvegarde dans un nouveau dossier. Les valeurs `--name` et les URLs sont celles de `/etc/kubernetes/manifests/etcd.yaml` :

```bash
kubectl -n kube-system exec etcd-controlplane -- etcdutl snapshot restore /var/lib/etcd/sauvegarde-tp11.db \
  --data-dir /var/lib/etcd/restauration \
  --name controlplane \
  --initial-cluster controlplane=https://10.10.0.10:2380 \
  --initial-advertise-peer-urls https://10.10.0.10:2380
```

Faites pointer etcd vers les données restaurées : dans `/etc/kubernetes/manifests/etcd.yaml`, changez le `hostPath` du volume `etcd-data` de `/var/lib/etcd` en `/var/lib/etcd/restauration`.

```bash
sudo cp /etc/kubernetes/manifests/etcd.yaml ~/etcd.yaml.bak
sudo vi /etc/kubernetes/manifests/etcd.yaml
watch -n 2 'sudo crictl ps --name "etcd|kube-apiserver"'
kubectl get ns                       # croustino-lyon est de retour
kubectl get pods -n croustino-lyon
```

> Si l'API server ne répond pas au bout de 2 minutes : `sudo systemctl restart kubelet`.

**Question :** que sont devenus les objets créés **après** la sauvegarde ?

### 4. Mettre à jour le cluster en v1.35 (30 min)

Dans un second terminal, surveillez le site pendant toute la mise à jour :

```bash
while true; do echo "$(date +%T) $(curl -s -o /dev/null -w '%{http_code}' http://10.10.0.11:30080/api/version)"; sleep 1; done
```

#### Control plane

```bash
sudo sed -i 's|/v1.34/|/v1.35/|' /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
apt-cache madison kubeadm | head -3
VERSION=1.35.X                       # remplacez X par la dernière version disponible

sudo apt-mark unhold kubeadm && sudo apt-get install -y kubeadm="$VERSION-*" && sudo apt-mark hold kubeadm
sudo kubeadm upgrade plan
sudo kubeadm upgrade apply "v$VERSION"

kubectl drain controlplane --ignore-daemonsets --delete-emptydir-data
sudo apt-mark unhold kubelet kubectl && sudo apt-get install -y kubelet="$VERSION-*" kubectl="$VERSION-*" && sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet
kubectl uncordon controlplane
```

#### Chaque worker, l'un après l'autre

```bash
# Sur le worker
sudo sed -i 's|/v1.34/|/v1.35/|' /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-mark unhold kubeadm && sudo apt-get install -y kubeadm="$VERSION-*" && sudo apt-mark hold kubeadm
sudo kubeadm upgrade node

# Sur le control plane
kubectl drain worker1 --ignore-daemonsets --delete-emptydir-data

# Sur le worker
sudo apt-mark unhold kubelet kubectl && sudo apt-get install -y kubelet="$VERSION-*" kubectl="$VERSION-*" && sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload && sudo systemctl restart kubelet

# Sur le control plane
kubectl uncordon worker1
kubectl get nodes
```

Pendant le drain de chaque worker, observez :

- les pods évincés et replanifiés (`kubectl get pods -n croustino -o wide -w`) ;
- le PDB qui ralentit le drain (`kubectl get pdb -n croustino`) ;
- **PostgreSQL** : où part-il ? Que voit le site ?

## Questions de fin

1. Pourquoi le site a-t-il renvoyé des erreurs pendant le drain d'un des workers ? Que faudrait-il changer ?
2. Listez les single points of failure de notre cluster et la solution pour chacun.
3. Pourquoi ne peut-on pas passer directement de la v1.34 à la v1.36 ?

## Bonus

- Planifiez une sauvegarde d'etcd quotidienne avec un CronJob qui tourne sur le control plane (tolérance, `nodeSelector`, `hostPath`).
- Vérifiez l'expiration des certificats après la mise à jour (`sudo kubeadm certs check-expiration`) : qu'a fait `kubeadm upgrade` ?
- Dessinez l'architecture cible de Croustino en haute disponibilité (3 control planes, load balancer, stockage répliqué).
