# Faire pointer etcd vers les données restaurées

> **Ne remplacez pas** `/etc/kubernetes/manifests/etcd.yaml` : on ne change **qu'une ligne**.

Sauvegarde d'abord, **hors** du dossier `manifests` :

```bash
sudo cp /etc/kubernetes/manifests/etcd.yaml ~/etcd.yaml.bak
sudo vi /etc/kubernetes/manifests/etcd.yaml
```

Tout en bas du fichier, dans la liste `volumes:`, repérez le volume `etcd-data` et changez son `path` :

```yaml
  - hostPath:
      path: /var/lib/etcd/restauration    # AVANT : /var/lib/etcd
      type: DirectoryOrCreate
    name: etcd-data
```

Ne touchez pas à `--data-dir=/var/lib/etcd` dans `command` : c'est le chemin **dans** le conteneur, qui reste le même.

Vérifiez qu'une seule ligne a changé :

```bash
sudo diff ~/etcd.yaml.bak /etc/kubernetes/manifests/etcd.yaml
```

Equivalent en une commande :

```bash
sudo sed -i 's|path: /var/lib/etcd$|path: /var/lib/etcd/restauration|' /etc/kubernetes/manifests/etcd.yaml
```
