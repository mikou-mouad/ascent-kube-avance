# TP 09 – « Qui a supprimé le back à 3h du matin ? »

**Durée :** 50 min · **Branche :** `tp-09-audit` · **Correction :** branche `tp-10-harbor` (`solutions/09-audit.md`)

## L'incident

> Samedi, 6h30. Les premiers livreurs ne voient aucune commande : le Deployment `back` a disparu de `croustino`.
> Grâce au TP 04, chacun a son identité… mais personne n'enregistre qui fait quoi. Les logs de l'API server ne disent rien.
> Sophie veut un coupable, Inès veut surtout que ça ne se reproduise pas.

## Objectifs

- Comprendre les niveaux et les étapes d'audit de l'API server.
- Écrire une politique d'audit qui garde l'essentiel sans noyer le disque.
- Activer l'audit sur un control plane kubeadm (static pod).
- Analyser les événements d'audit avec `jq`.

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-09-audit
```

La branche contient l'état attendu à la fin du TP précédent (c'est aussi sa correction).
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Étapes

### 1. Lire la politique

Lisez `k8s/audit/audit-policy.yaml`.

**Questions :** à quel niveau sera enregistrée la lecture d'un Secret ? La suppression d'un Deployment dans `croustino` ? La création d'un namespace ? Pourquoi ne jamais mettre les Secrets au niveau `RequestResponse` ?

### 2. Activer l'audit (control plane)

```bash
sudo mkdir -p /etc/kubernetes/audit /var/log/kubernetes/audit
sudo cp k8s/audit/audit-policy.yaml /etc/kubernetes/audit/policy.yaml
# Sauvegarde HORS du dossier manifests (sinon le kubelet lancerait deux API servers)
sudo cp /etc/kubernetes/manifests/kube-apiserver.yaml ~/kube-apiserver.yaml.bak
sudo vi /etc/kubernetes/manifests/kube-apiserver.yaml
```

Dans `kube-apiserver.yaml`, ajoutez :

```yaml
# spec.containers[0].command
    - --audit-policy-file=/etc/kubernetes/audit/policy.yaml
    - --audit-log-path=/var/log/kubernetes/audit/audit.log
    - --audit-log-maxage=7
    - --audit-log-maxbackup=3
    - --audit-log-maxsize=50

# spec.containers[0].volumeMounts
    - name: audit-policy
      mountPath: /etc/kubernetes/audit
      readOnly: true
    - name: audit-log
      mountPath: /var/log/kubernetes/audit

# spec.volumes
  - name: audit-policy
    hostPath:
      path: /etc/kubernetes/audit
      type: DirectoryOrCreate
  - name: audit-log
    hostPath:
      path: /var/log/kubernetes/audit
      type: DirectoryOrCreate
```

Le kubelet redémarre l'API server tout seul. Patientez (1 à 2 minutes) :

```bash
watch -n 2 'sudo crictl ps --name kube-apiserver; kubectl get nodes'
sudo tail -f /var/log/kubernetes/audit/audit.log | head -3
```

> L'API server ne revient pas ? `sudo crictl ps -a --name kube-apiserver`, puis `sudo crictl logs <id>`. En dernier recours, restaurez la sauvegarde.

### 3. Rejouer la nuit de vendredi

Lancez les commandes suivantes en vous faisant passer pour les utilisateurs du TP 04 (le formateur peut aussi en ajouter) :

```bash
export M=~/utilisateurs/malik/malik.kubeconfig T=~/utilisateurs/theo/theo.kubeconfig
KUBECONFIG=$T kubectl delete deployment back -n croustino          # refusé
KUBECONFIG=$M kubectl get secrets -n croustino                      # refusé
KUBECONFIG=$M kubectl scale deployment front --replicas=3 -n croustino
KUBECONFIG=$M kubectl delete deployment back -n croustino           # le coupable
```

Remettez le back en place : `helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml`.

### 4. Mener l'enquête

```bash
sudo apt-get install -y jq
A=/var/log/kubernetes/audit/audit.log
```

Écrivez une requête `jq` pour chaque question :

1. Qui a supprimé le Deployment `back`, à quelle heure, depuis quelle IP, avec quel outil (`userAgent`) ?
2. Quelles requêtes ont été **refusées** (`responseStatus.code` 403) et pour qui ?
3. Qui a modifié le nombre de réplicas du front, et quelle était la nouvelle valeur ?
4. Combien d'événements par utilisateur depuis l'activation ?

Point de départ :

```bash
sudo jq -c 'select(.verb=="delete") | {t: .requestReceivedTimestamp, qui: .user.username, quoi: .objectRef}' $A
```

## Questions de fin

1. Quelle est la taille du fichier au bout de 30 minutes ? Que se passerait-il sur un gros cluster avec le niveau `RequestResponse` partout ?
2. Pourquoi l'audit doit-il partir vers un système externe en production ?
3. L'audit empêche-t-il l'incident ? Que faut-il en plus ?

## Bonus

- Envoyez l'audit dans Elasticsearch : un pod Fluent Bit sur le control plane (tolérance) qui lit `/var/log/kubernetes/audit/audit.log`.
- Utilisez le backend webhook (`--audit-webhook-config-file`) au lieu du fichier.
- Ajoutez une règle qui trace au niveau `Request` les `pods/exec` : qui ouvre un shell dans un conteneur ?
