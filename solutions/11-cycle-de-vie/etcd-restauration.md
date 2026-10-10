# Remettre etcd sur les données restaurées

Après `etcdutl snapshot restore … --data-dir /var/lib/etcd/restauration`, les données restaurées sont dans un dossier à part. On les met à la place des données actuelles, **sans modifier** `etcd.yaml` :

```bash
sudo mv /etc/kubernetes/manifests/etcd.yaml /root/etcd.yaml        # etcd s'arrête
sudo crictl ps --name etcd -q                                      # attendre que plus rien ne s'affiche

sudo mv /var/lib/etcd/restauration /var/lib/etcd-restauration
sudo mv /var/lib/etcd /var/lib/etcd-avant-restauration             # l'ancien est gardé, par sécurité
sudo mv /var/lib/etcd-restauration /var/lib/etcd

sudo mv /root/etcd.yaml /etc/kubernetes/manifests/etcd.yaml        # etcd redémarre
```

## Pourquoi ne pas changer le hostPath dans etcd.yaml ?

Ça fonctionne… jusqu'à la mise à jour. kubeadm garde sa configuration dans la ConfigMap `kubeadm-config`, où les données d'etcd sont dans `/var/lib/etcd`. `kubeadm upgrade apply` régénère `etcd.yaml` à partir d'elle : etcd repart sur les données **d'avant** la restauration, le control plane ne se stabilise pas, et kubeadm annule la mise à jour (`Failed to upgrade etcd … context deadline exceeded`).

## Si le hostPath a déjà été changé

Même procédure, en remettant le chemin d'origine dans le manifest avant de le replacer :

```bash
sudo mv /etc/kubernetes/manifests/etcd.yaml /root/etcd.yaml
sudo crictl ps --name etcd -q                                      # attendre que plus rien ne s'affiche
sudo mv /var/lib/etcd/restauration /var/lib/etcd-restauration
sudo mv /var/lib/etcd /var/lib/etcd-avant-restauration
sudo mv /var/lib/etcd-restauration /var/lib/etcd
sudo sed -i 's|path: /var/lib/etcd/restauration$|path: /var/lib/etcd|' /root/etcd.yaml
sudo mv /root/etcd.yaml /etc/kubernetes/manifests/etcd.yaml
```

Si un `kubeadm upgrade apply` a échoué entre-temps, supprimez les Jobs `upgrade-health-check-…` restés dans `kube-system` avant de le relancer :

```bash
kubectl -n kube-system get jobs
kubectl -n kube-system delete job <nom-du-job>
```
