# Remettre etcd sur les données restaurées

Après `etcdutl snapshot restore … --data-dir /var/lib/etcd/restauration`, les données restaurées sont dans un dossier à part. On arrête **tout le control plane**, on met les données restaurées à la place des anciennes, puis on relance tout, **sans modifier aucun manifest** :

```bash
sudo mkdir -p /root/manifests-arretes
sudo mv /etc/kubernetes/manifests/*.yaml /root/manifests-arretes/   # le control plane s'arrête
sudo crictl ps --name "etcd|kube-apiserver|kube-controller-manager|kube-scheduler" -q
# relancer la commande précédente jusqu'à ce qu'elle n'affiche plus rien

sudo mv /var/lib/etcd/restauration /var/lib/etcd-restauration
sudo mv /var/lib/etcd /var/lib/etcd-avant-restauration             # l'ancien est gardé, par sécurité
sudo mv /var/lib/etcd-restauration /var/lib/etcd

sudo mv /root/manifests-arretes/*.yaml /etc/kubernetes/manifests/   # le control plane redémarre
sudo systemctl restart kubelet
```

## Pourquoi arrêter aussi l'API server ?

Il garde en mémoire un cache de tous les objets, construit à partir de l'ancien etcd. S'il tourne pendant la restauration, ce cache ne correspond plus aux données (`Cache consistency check failed` dans ses logs). Les mirror pods des static pods ne sont plus mis à jour (`etcd-controlplane` reste `Pending`), et `kubeadm upgrade apply` échoue en attendant etcd (`Failed to upgrade etcd … context deadline exceeded`).

La documentation de Kubernetes demande d'arrêter les API servers pendant une restauration, puis de redémarrer l'API server, le controller-manager, le scheduler et le kubelet.

## Pourquoi ne pas changer le hostPath dans etcd.yaml ?

Ça fonctionne… jusqu'à la mise à jour. kubeadm garde sa configuration dans la ConfigMap `kubeadm-config`, où les données d'etcd sont dans `/var/lib/etcd`. `kubeadm upgrade apply` régénère `etcd.yaml` à partir d'elle : etcd repart sur les données **d'avant** la restauration.

## Réparer un cluster déjà dans cet état

**Le `hostPath` d'`etcd.yaml` a été changé** (`grep -B3 "name: etcd-data" /etc/kubernetes/manifests/etcd.yaml` affiche `/var/lib/etcd/restauration`) : refaire la procédure ci-dessus, en remettant le chemin d'origine avant de replacer les manifests :

```bash
sudo sed -i 's|path: /var/lib/etcd/restauration$|path: /var/lib/etcd|' /root/manifests-arretes/etcd.yaml
```

**L'API server a tourné pendant la restauration** (`Cache consistency check failed`, `etcd-controlplane` en `Pending`) :

```bash
sudo crictl stop $(sudo crictl ps --name "kube-apiserver|kube-controller-manager|kube-scheduler" -q)
sudo systemctl restart kubelet
kubectl -n kube-system get pods | grep -E "etcd|apiserver"     # etcd-controlplane doit être Running
kubectl -n kube-system delete pod etcd-controlplane            # s'il reste Pending : le kubelet recrée le mirror pod
```

**Un `kubeadm upgrade apply` a échoué entre-temps** : supprimez les Jobs `upgrade-health-check-…` restés dans `kube-system` avant de le relancer, et ne l'interrompez pas avec Ctrl+C.

```bash
kubectl -n kube-system get jobs
kubectl -n kube-system delete job <nom-du-job>
```
