# Activer l'audit dans kube-apiserver.yaml

> **Ne remplacez pas** `/etc/kubernetes/manifests/kube-apiserver.yaml` par ce qui suit : ce fichier, généré par kubeadm, contient d'autres lignes indispensables (image, certificats, autres volumes). On **ajoute** trois blocs, sans rien effacer.

Sauvegarde d'abord, **hors** du dossier `manifests` :

```bash
sudo cp /etc/kubernetes/manifests/kube-apiserver.yaml ~/kube-apiserver.yaml.bak
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
```

## 1. Les options, à la fin de la liste `command`

Sous `spec.containers[0].command`, après la dernière ligne qui commence par `- --` (même indentation) :

```yaml
    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml
    - --audit-log-path=/var/log/kubernetes/audit/audit.log
    - --audit-log-maxage=7
    - --audit-log-maxbackup=3
    - --audit-log-maxsize=50
```

## 2. Les montages, à la fin de `volumeMounts`

Dans le conteneur, à la fin de la liste `volumeMounts:` (même indentation que les `- mountPath:` existants) :

```yaml
    - mountPath: /etc/kubernetes/audit
      name: audit-policy
      readOnly: true
    - mountPath: /var/log/kubernetes/audit
      name: audit-log
```

## 3. Les volumes, à la fin de `volumes`

Tout en bas du fichier, à la fin de la liste `volumes:` (même indentation que les `- hostPath:` existants) :

```yaml
  - hostPath:
      path: /etc/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-policy
  - hostPath:
      path: /var/log/kubernetes/audit
      type: DirectoryOrCreate
    name: audit-log
```

## Vérifier avant d'attendre

Seules des lignes ajoutées (`>`) doivent apparaître :

```bash
sudo diff ~/kube-apiserver.yaml.bak /etc/kubernetes/manifests/kube-apiserver.yaml
```

Le kubelet redémarre l'API server dans les 1 à 2 minutes. S'il refuse le fichier, la cause est dans :

```bash
sudo journalctl -u kubelet --since "5 min ago" --no-pager | grep -i "manifest" | tail -5
```
