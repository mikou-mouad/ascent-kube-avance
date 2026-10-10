# Correction du TP 04 – Authentification et RBAC

## YAML prêts à l'emploi

Pour ceux qui n'ont pas réussi à les écrire, dans ce dossier :

- `csr-malik.yaml` : la CertificateSigningRequest de l'étape 2 (la commande pour y insérer `malik.csr` est en commentaire)
- `bonus-rbac.yaml` : le ClusterRole agrégé à `view` et la lecture des logs de `kube-system` pour Malik
- La création complète d'un utilisateur, kubeconfig compris : `tp/04-rbac/creer-utilisateur.sh`

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `k8s/20-back.yaml`
- `k8s/rbac/10-utilisateurs.yaml`
- `k8s/rbac/20-serviceaccounts.yaml`

Pour les comparer à votre travail : `diff -r solutions/04-rbac/k8s k8s` (ou `helm`).

Manifests : `k8s/rbac/` et `serviceAccountName: back` dans `k8s/20-back.yaml`.

- **kubernetes-admin :** son certificat porte `O=kubeadm:cluster-admins` (anciennement `system:masters`), groupe lié à `cluster-admin`.
- **Malik avant RBAC :** authentifié (`auth whoami` répond), mais `Forbidden` : aucune règle ne l'autorise. RBAC refuse tout par défaut.
- **RoleBinding vers un ClusterRole :** on réutilise la définition `view` mais les droits restent limités au namespace du RoleBinding. Un ClusterRoleBinding donnerait la lecture sur tout le cluster.
- **Incident rejoué :** `deployments.apps is forbidden: User "theo" cannot delete resource...`.
- **Token du back :** le pod recevait un token inutile. Si le back était compromis, ce token donnerait accès à l'API. `automountServiceAccountToken: false` le supprime.
- **Révoquer Théo :** on ne peut pas révoquer un certificat client dans Kubernetes. On supprime ses bindings (il reste authentifié mais n'a plus aucun droit) et on utilise des certificats courts. D'où l'intérêt de binder des groupes et des identités gérées ailleurs.
- **Groupes :** les arrivées et départs se gèrent dans l'annuaire, pas dans Kubernetes.
- **En entreprise :** OIDC (Keycloak, Entra ID, Dex…) avec des groupes issus de l'annuaire. Les certificats sont réservés aux comptes de secours.
