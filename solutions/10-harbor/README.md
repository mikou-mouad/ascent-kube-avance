# Correction du TP 10 – Harbor

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `README.md`
- `helm/croustino/values-rennes.yaml`
- `programme-3-jours.md`

Pour les comparer à votre travail : `diff -r solutions/10-harbor/k8s k8s` (ou `helm`).

`helm/croustino/values-rennes.yaml` pointe maintenant vers `10.10.0.10:30002/croustino` avec le secret `harbor-croustino`.

- **Composants :** `core` (API et logique), `portal` (interface web), `registry` (stockage des images), `jobservice` (scans, réplications, nettoyage), `trivy` (scanner), `database` (PostgreSQL), `redis` (cache et files de tâches), `nginx` (point d'entrée en mode NodePort).
- **Scan :** `nginx:1.19` (2020) remonte des dizaines de vulnérabilités, dont des critiques. `croustino-front:1.1`, construite sur une image récente, en a beaucoup moins.
- **Image vulnérable bloquée :** le pull échoue (`ErrImagePull`), avec un message de Harbor indiquant que l'image ne respecte pas la politique de sévérité du projet.
- **Harbor indisponible :** les pods déjà lancés continuent (images en cache sur les nœuds), mais un pod replanifié sur un autre nœud ne démarre pas. Mettre Harbor en haute disponibilité (stockage objet S3, base et Redis externes, plusieurs réplicas), le superviser, et répliquer vers un second registre.
- **Registre public qui limite :** un projet **proxy cache**. Le cluster tire `harbor/dockerhub/library/postgres:16` : Harbor ne télécharge l'image qu'une fois, puis la sert depuis son cache.
- **Robot :** des droits limités à un projet et à des actions (pull/push), révocables et renouvelables sans toucher au compte admin. Le secret stocké dans le cluster ne donne pas les clés de tout Harbor.
