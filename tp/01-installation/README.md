# TP 01 – « Il nous faut un vrai cluster »

**Durée :** 2 h · **Branche :** `tp-01-installation` · **Correction :** branche `tp-02-deploiement` (`solutions/01-installation.md`)

## L'incident

> Lundi, 7h12. La VM de Croustino est à 100 % de CPU. Malik redémarre le back pour déployer un correctif : le site est coupé 4 minutes, en plein rush.
> 37 commandes sont perdues. Sophie tranche : « On passe sur Kubernetes. Inès, il nous faut un cluster. »

Inès dispose de 3 VM Ubuntu. Elle veut un cluster kubeadm standard : 1 control plane, 2 workers.

## Objectifs

- Préparer des nœuds Linux pour Kubernetes et comprendre pourquoi chaque réglage est nécessaire.
- Initialiser un control plane avec kubeadm et identifier les composants créés.
- Installer un CNI et joindre des workers.
- Valider le fonctionnement du réseau du cluster.

## Étapes

Suivez le [guide d'installation](../../guide-installation-cluster.md), sections 2 à 7.
À chaque étape, répondez aux questions ci-dessous (on les corrige ensemble).

### 1. Préparation des nœuds (sections 2 et 3)

1. Pourquoi le kubelet refuse-t-il de démarrer si le swap est actif ?
2. À quoi servent le module `br_netfilter` et `net.ipv4.ip_forward` ?
3. Que se passe-t-il si containerd utilise le driver cgroup `cgroupfs` alors que le kubelet utilise `systemd` ?
4. Pourquoi bloque-t-on les paquets avec `apt-mark hold` ?

### 2. Control plane (section 4)

Après `kubeadm init` :

```bash
ls /etc/kubernetes/manifests/
kubectl get pods -n kube-system -o wide
kubectl get nodes
```

5. Quels composants tournent en **static pods** ? Qui les démarre ?
6. Pourquoi le nœud est-il `NotReady` ?
7. Où sont rangés les certificats du cluster ? Combien de temps sont-ils valides (`sudo kubeadm certs check-expiration`) ?

### 3. Réseau et workers (sections 5 et 6)

8. Combien de pods `calico-node` attendez-vous, et pourquoi ?
9. Le token de `kubeadm join` expire au bout de combien de temps ?

### 4. Validation (section 7)

Réalisez tous les tests de la section 7. Critères de réussite :

- [ ] 3 nœuds `Ready`
- [ ] la page nginx est renvoyée par le test busybox (DNS + réseau des services)
- [ ] `HTTP/1.1 200 OK` sur le NodePort des 3 nœuds

### 5. Point de restauration

- Supprimez les objets de test nginx.
- Prenez un **snapshot des 3 VM**. Vous y reviendrez en cas de problème pendant la formation.

Le dépôt de la formation sera cloné sur le control plane au début du TP 02.

## Bonus

- Activez l'autocomplétion : `echo 'source <(kubectl completion bash)' >> ~/.bashrc` et l'alias `alias k=kubectl` avec `complete -o default -F __start_kubectl k`.
- Retrouvez dans `/etc/kubernetes/manifests/kube-apiserver.yaml` le CIDR des services et le mode d'autorisation.
- Copiez le kubeconfig sur votre poste pour piloter le cluster à distance.
