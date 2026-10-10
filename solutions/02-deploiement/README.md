# Correction du TP 02 – Déploiement de Croustino

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `k8s/01-secret.yaml`
- `k8s/02-configmap.yaml`
- `k8s/20-back.yaml`
- `k8s/30-front.yaml`

Pour les comparer à votre travail : `diff -r solutions/02-deploiement/k8s k8s` (ou `helm`).

Les manifests complets sont dans `k8s/`.

- **Secret :** les valeurs sont seulement encodées en base64, pas chiffrées. Toute personne qui peut lire les Secrets du namespace lit le mot de passe (on le verrouille au TP 04). Le chiffrement au repos dans etcd se configure à part (`EncryptionConfiguration`).
- **Mot de passe de PostgreSQL :** `envFrom.secretRef` injecte chaque clé du Secret comme variable d'environnement.
- **readinessProbe :** tant qu'elle échoue, le pod n'est pas ajouté aux endpoints du Service et ne reçoit pas de trafic.
- **Sélecteur vide de correspondance :** le Service existe, mais n'a aucun endpoint. Les connexions échouent (refus ou timeout).
- **Endpoints du back :** `/readyz` teste la base. Tant que PostgreSQL n'est pas prêt, le back reste `0/1 Ready` et n'est pas exposé.
- **Gains par rapport à la VM :** redémarrage automatique, scaling, mise à jour sans coupure, configuration séparée du code.
  **Ce qui manque :** les données de PostgreSQL vivent dans le conteneur. C'est le prochain incident.
