# TP 04 – « Le stagiaire a supprimé la prod »

**Durée :** 2 h 05 (en deux parties) · **Branche :** `tp-04-rbac` · **Correction :** branche `tp-05-capacite` (`k8s/rbac/`)

## L'incident

> Croustino a recruté. Pour aller vite, Inès a donné à tout le monde une copie de `admin.conf`.
> Jeudi, 6h50, Théo, le stagiaire, nettoie « son » namespace de test… avec le mauvais contexte. `kubectl delete deployment --all` part sur `croustino`.
> Personne ne sait qui a fait quoi : tout le monde s'appelle `kubernetes-admin`.

## Objectifs

- Comprendre comment Kubernetes identifie un utilisateur (certificat X.509 : CN = nom, O = groupe).
- Créer des utilisateurs avec l'API CertificateSigningRequest et des kubeconfigs dédiés.
- Donner des droits minimaux avec Role, ClusterRole, RoleBinding et ClusterRoleBinding.
- Utiliser des ServiceAccounts pour les applications et la CI.

## Les besoins de Croustino

| Personne / application | Identité | Droits attendus |
|------------------------|----------|-----------------|
| Inès (admin) | utilisateur `ines`, groupe `ops` | administratrice du cluster |
| Malik (dev) | utilisateur `malik`, groupe `dev` | gérer pods, Deployments, Services, ConfigMaps dans `croustino`, lire les logs, faire un `exec`. **Pas** d'accès aux Secrets |
| Théo (stagiaire) | utilisateur `theo`, groupe `stagiaires` | lecture seule dans `croustino` |
| Le back | ServiceAccount `back` | aucun accès à l'API (il n'en a pas besoin) |
| La CI | ServiceAccount `ci-deployer` | mettre à jour l'image des Deployments de `croustino`, rien d'autre |

## Partie 1 – Authentification (40 min)

### 1. Qui suis-je ?

```bash
kubectl auth whoami
openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -subject -issuer
grep client-certificate-data ~/.kube/config | awk '{print $2}' | base64 -d | openssl x509 -noout -subject
```

**Question :** pourquoi l'utilisateur `kubernetes-admin` peut-il tout faire ? (indice : son groupe)

### 2. Créer Malik à la main

Suivez les étapes, une par une, en lisant le script `creer-utilisateur.sh` :

1. Générez une clé et une demande de certificat avec `CN=malik` et `O=dev`.
2. Créez l'objet `CertificateSigningRequest`, observez-le avec `kubectl get csr`.
3. Approuvez-le, récupérez le certificat signé.
4. Construisez `malik.kubeconfig` avec `kubectl config set-cluster / set-credentials / set-context`.

```bash
KUBECONFIG=~/utilisateurs/malik/malik.kubeconfig kubectl auth whoami
KUBECONFIG=~/utilisateurs/malik/malik.kubeconfig kubectl get pods
```

**Question :** Malik est authentifié, mais que répond l'API ? Pourquoi ?

### 3. Créer Théo et Inès avec le script

```bash
chmod +x tp/04-rbac/creer-utilisateur.sh
tp/04-rbac/creer-utilisateur.sh theo stagiaires
tp/04-rbac/creer-utilisateur.sh ines ops
```

## Partie 2 – Autorisation (1 h 25)

Écrivez vos manifests dans `k8s/rbac/`.

### 4. Théo : lecture seule

Utilisez le ClusterRole intégré `view` avec un **RoleBinding** dans `croustino` (et non un ClusterRoleBinding : pourquoi ?).

```bash
kubectl get clusterrole view -o yaml | less
kubectl auth can-i delete deployments -n croustino --as theo --as-group stagiaires
```

### 5. Malik : un rôle sur mesure

Écrivez un **Role** `developpeur` dans `croustino` et liez-le au **groupe** `dev`.
Aidez-vous de `kubectl api-resources -o wide` pour trouver les groupes d'API et les verbes.

Vérifiez :

```bash
kubectl auth can-i --list -n croustino --as malik --as-group dev
kubectl auth can-i get secrets -n croustino --as malik --as-group dev       # no
kubectl auth can-i create pods/exec -n croustino --as malik --as-group dev  # yes
kubectl auth can-i get pods -n kube-system --as malik --as-group dev        # no
```

### 6. Inès : administratrice

Liez le groupe `ops` au ClusterRole `cluster-admin`. Désormais, Inès utilise son propre kubeconfig, plus `admin.conf`.

### 7. Rejouer l'incident

```bash
export KUBECONFIG=~/utilisateurs/theo/theo.kubeconfig
kubectl get pods
kubectl delete deployment --all
unset KUBECONFIG
```

### 8. ServiceAccounts

1. Regardez le token monté dans un pod du back : `kubectl exec deploy/back -- ls /var/run/secrets/kubernetes.io/serviceaccount/`. Le back utilise-t-il l'API Kubernetes ?
2. Créez le ServiceAccount `back` avec `automountServiceAccountToken: false` et utilisez-le dans `k8s/20-back.yaml` (`serviceAccountName`).
3. Créez le ServiceAccount `ci-deployer` et un Role `deployer` limité à `get` et `patch` sur les `deployments`.
4. Testez la CI avec un token court :

```bash
TOKEN=$(kubectl create token ci-deployer -n croustino --duration=10m)
# kubeconfig vide : sinon le certificat admin serait utilisé avant le token
alias kci="kubectl --kubeconfig=/dev/null --server=https://10.10.0.10:6443 \
  --certificate-authority=/etc/kubernetes/pki/ca.crt --token=$TOKEN -n croustino"

kci auth whoami
kci set image deployment/front front=ghcr.io/mikou-mouad/croustino-front:1.0
kci get secrets        # Forbidden
kci set image deployment/front front=ghcr.io/mikou-mouad/croustino-front:1.1
```

## Questions de fin

1. Comment révoquer l'accès de Théo avant l'expiration de son certificat ?
2. Pourquoi binder des **groupes** plutôt que des utilisateurs ?
3. En entreprise, quelle méthode d'authentification remplacerait les certificats ?

## Bonus

- Décodez le token de `ci-deployer` (partie centrale, base64) : audience, expiration, liaison au ServiceAccount.
- Créez un ClusterRole `lecteur-croustino` agrégé au rôle `view` (`aggregationRule` / label `rbac.authorization.k8s.io/aggregate-to-view`).
- Donnez à Malik le droit de lire les logs dans `kube-system` sans rien d'autre.
