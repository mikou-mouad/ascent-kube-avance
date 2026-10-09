# TP 10 – « Docker Hub nous bloque au rush »

**Durée :** 50 min · **Branche :** `tp-10-harbor` · **Correction :** branche `tp-11-cycle-de-vie` (`helm/croustino/values-rennes.yaml`, `solutions/10-harbor.md`)

## L'incident

> Lundi, 6h45. Un nœud redémarre, ses pods doivent retélécharger leurs images. Le registre public répond « too many requests » : 20 minutes sans back.
> Le même jour, un audit de sécurité signale une image de base vieille de 3 ans, avec des failles critiques connues.
> Inès décide d'héberger les images de Croustino chez Croustino, et de les scanner.

## Objectifs

- Déployer Harbor avec Helm.
- Organiser les images : projets, visibilité, comptes robots.
- Scanner les images avec Trivy et bloquer les images vulnérables.
- Faire tirer les images du cluster depuis un registre privé (containerd, imagePullSecret).

## Étapes

### 0. Libérer de la mémoire

Harbor a besoin d'environ 2 Go. Retirez la chaîne de logs du TP 08 :

```bash
helm uninstall fluent-bit -n logging
kubectl delete -f k8s/logs/elasticsearch-kibana.yaml
kubectl top nodes
```

### 1. Installer Harbor

Adaptez `externalURL` dans `k8s/harbor/values-harbor.yaml` si votre control plane n'est pas en `10.10.0.10`.

```bash
helm repo add harbor https://helm.goharbor.io
helm install harbor harbor/harbor -n harbor --create-namespace -f k8s/harbor/values-harbor.yaml
kubectl get pods -n harbor -w
```

**Question :** quels composants composent Harbor (`kubectl get deploy,sts -n harbor`) ? À quoi sert chacun ?

### 2. Organiser le registre

Ouvrez `http://10.10.0.10:30002` (admin / Harbor12345).

1. Créez le projet **croustino**, **privé**.
2. Dans le projet, créez un **compte robot** `cluster` avec les droits *pull* et *push* sur les dépôts. Notez son nom complet (`robot$croustino+cluster`) et son secret.

### 3. Copier les images dans Harbor

Le control plane n'a pas Docker : on utilise `skopeo`, qui copie des images de registre à registre.

```bash
sudo apt-get install -y skopeo
H=10.10.0.10:30002
ROBOT='robot$croustino+cluster'      # guillemets simples : $ dans le nom !
read -rs -p "Secret du robot : " SECRET; echo

for img in croustino-back:1.0 croustino-front:1.0 croustino-front:1.1; do
  skopeo copy --dest-tls-verify=false --dest-creds "$ROBOT:$SECRET" \
    docker://ghcr.io/mikou-mouad/$img docker://$H/croustino/$img
done

# Une vieille image, pour comparer
skopeo copy --dest-tls-verify=false --dest-creds "$ROBOT:$SECRET" \
  docker://docker.io/library/nginx:1.19 docker://$H/croustino/nginx:1.19
```

### 4. Scanner

1. Dans le projet, sélectionnez les images et lancez **Scan vulnerability**.
2. Comparez `nginx:1.19` et `croustino-front:1.1`. Combien de vulnérabilités critiques ?
3. Dans **Configuration** du projet, activez **Prevent vulnerable images from running** (sévérité *Critical*) et **Automatically scan images on push**.

### 5. Faire confiance au registre (sur les 3 nœuds)

Harbor est en HTTP : containerd doit l'accepter explicitement.

```bash
sudo sed -i 's|config_path = ""|config_path = "/etc/containerd/certs.d"|' /etc/containerd/config.toml
grep -n 'config_path' /etc/containerd/config.toml
sudo mkdir -p /etc/containerd/certs.d/10.10.0.10:30002
cat <<EOF | sudo tee /etc/containerd/certs.d/10.10.0.10:30002/hosts.toml
server = "http://10.10.0.10:30002"

[host."http://10.10.0.10:30002"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF
sudo systemctl restart containerd
```

### 6. Croustino tiré depuis Harbor

```bash
kubectl create secret docker-registry harbor-croustino -n croustino \
  --docker-server=10.10.0.10:30002 --docker-username="$ROBOT" --docker-password="$SECRET"
```

Modifiez `helm/croustino/values-rennes.yaml` pour utiliser le registre Harbor (`imageRegistry`) et le secret (`imagePullSecrets`), puis :

```bash
helm upgrade croustino helm/croustino -n croustino -f helm/croustino/values-rennes.yaml
kubectl get pods -n croustino -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
kubectl describe pod -n croustino -l app=back | grep -i pulled
```

Enfin, essayez de lancer l'image vulnérable :

```bash
kubectl run vieux -n croustino --image=10.10.0.10:30002/croustino/nginx:1.19 \
  --overrides='{"spec":{"imagePullSecrets":[{"name":"harbor-croustino"}]}}'
kubectl describe pod vieux -n croustino | tail -5
kubectl delete pod vieux -n croustino
```

## Questions de fin

1. Que se passe-t-il pour Croustino si Harbor tombe ? Comment le rendre plus robuste ?
2. Quelle fonctionnalité de Harbor règle directement le problème du registre public qui limite les téléchargements ?
3. Pourquoi un compte robot plutôt que le compte admin dans le cluster ?

## Bonus

- Créez un projet **proxy cache** `dockerhub` pointant vers Docker Hub, et faites tirer `postgres:16` via `10.10.0.10:30002/dockerhub/library/postgres:16`.
- Publiez le chart Croustino dans Harbor : `helm registry login 10.10.0.10:30002 --insecure`, `helm package helm/croustino`, puis `helm push croustino-0.1.0.tgz oci://10.10.0.10:30002/croustino --plain-http`.
- Ajoutez une règle de rétention : garder les 3 derniers tags de chaque dépôt.
