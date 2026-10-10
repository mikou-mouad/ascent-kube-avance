# TP 06 – « On ouvre à Lyon »

**Durée :** 1 h 15 · **Branche :** `tp-06-helm` · **Correction :** branche `tp-07-monitoring` (`helm/croustino/`)

## L'incident

> Croustino ouvre à Lyon lundi prochain. Malik copie le dossier `k8s/` en `k8s-lyon/` et remplace « Rennes » à la main.
> Deux semaines plus tard, un correctif est appliqué à Rennes mais oublié à Lyon. Le NodePort est en conflit, la ville affichée est fausse, et personne ne sait quelle version tourne où.

## Objectifs

- Comprendre ce qu'apporte Helm : chart, templates, values, release, historique.
- Transformer les manifests de Croustino en chart paramétrable.
- Reprendre une application existante dans Helm sans perdre les données.
- Déployer plusieurs instances, mettre à jour et revenir en arrière.

## Avant de commencer : passer sur la branche du TP

Sur le **control plane** :

```bash
cd ~/croustino
git fetch
git stash -u          # met de côté vos fichiers du TP précédent
git checkout tp-06-helm
```

La branche contient l'état attendu à la fin du TP précédent (c'est aussi sa correction).
Vos propres fichiers restent récupérables avec `git stash list` et `git stash show -p`.

## Étapes

### 1. Installer Helm

```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

### 2. Découvrir la structure d'un chart

```bash
helm create /tmp/demo
tree /tmp/demo
helm template demo /tmp/demo | less
```

Repérez `Chart.yaml`, `values.yaml`, `templates/`, `_helpers.tpl`, `NOTES.txt`.

### 3. Créer le chart Croustino

Créez `helm/croustino/` à la main (sans `helm create`) :

```
helm/croustino/
├── Chart.yaml
├── values.yaml           # valeurs par défaut
├── values-rennes.yaml    # ce qui change à Rennes
├── values-lyon.yaml      # ce qui change à Lyon
└── templates/
    ├── _helpers.tpl
    ├── secret.yaml
    ├── configmap.yaml
    ├── serviceaccount.yaml
    ├── postgres.yaml
    ├── back.yaml
    ├── front.yaml
    └── NOTES.txt
```

Partez des fichiers de `k8s/` et paramétrez au minimum :

| Valeur | Rennes | Lyon |
|--------|--------|------|
| `ville` | Rennes | Lyon |
| `front.nodePort` | 30080 | 30081 |
| `front.image.tag` | 1.1 | 1.1 |
| `back.replicas` | 2 | 1 |
| `stockMax` | 24 | 12 |

Ajoutez aussi `imageRegistry` (par défaut `ghcr.io/mikou-mouad`) et `imagePullSecrets` (liste vide) : ils serviront au TP 10.

Le namespace ne doit **pas** être écrit en dur : utilisez `{{ .Release.Namespace }}`.

Vérifiez sans rien installer :

```bash
helm lint helm/croustino -f helm/croustino/values-rennes.yaml
helm template croustino helm/croustino -f helm/croustino/values-lyon.yaml | less
```

### 4. Reprendre Rennes dans Helm sans perdre les commandes

Helm refuse de gérer des objets qu'il n'a pas créés. On supprime donc les objets de l'application, **sauf le PVC** :

```bash
kubectl get pvc -n croustino                       # data-postgres-0 : à garder !
kubectl delete -f k8s/30-front.yaml -f k8s/20-back.yaml -f k8s/10-postgres.yaml \
  -f k8s/02-configmap.yaml -f k8s/01-secret.yaml
kubectl delete serviceaccount back -n croustino
kubectl get pvc -n croustino                       # toujours là
helm install croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml
```

Vérifiez sur le site que les anciennes commandes sont toujours là. **Pourquoi** le StatefulSet a-t-il retrouvé le volume ?

### 5. Ouvrir Lyon

```bash
kubectl create namespace croustino-lyon
helm install croustino-lyon helm/croustino -n croustino-lyon -f helm/croustino/values-lyon.yaml
helm list -A
```

Ouvrez `http://<IP d'un nœud>:30081` : le bandeau affiche Lyon.

### 6. Mettre à jour et revenir en arrière

```bash
helm upgrade croustino-lyon helm/croustino -n croustino-lyon \
  -f helm/croustino/values-lyon.yaml --set front.image.tag=1.0
helm history croustino-lyon -n croustino-lyon
helm rollback croustino-lyon 1 -n croustino-lyon
helm get values croustino-lyon -n croustino-lyon
```

## Questions de fin

1. Où Helm stocke-t-il l'historique des releases ?
2. Différence entre `helm upgrade --set` et une modification de `values-lyon.yaml` commitée ?
3. Que faudrait-il ajouter pour appliquer LimitRange et ResourceQuota à Lyon ?

## Bonus

- Ajoutez un `checksum/config` en annotation du back pour le redémarrer automatiquement quand la ConfigMap change.
- Empaquetez le chart (`helm package`) et publiez-le dans un registre OCI (vous le ferez dans Harbor au TP 10).
- Installez le plugin `helm-diff` et comparez deux révisions avant un upgrade.
