# Kubernetes – Avancé : supports de formation

Formation de 3 jours racontée à travers l'histoire de **Croustino**, une entreprise de livraison de croissants qui migre son application d'une VM vers Kubernetes.

- [programme-3-jours.md](programme-3-jours.md) : le programme détaillé et le fil rouge
- [guide-installation-cluster.md](guide-installation-cluster.md) : installation du cluster de TP (kubeadm, containerd, Calico)
- `app/` : l'application Croustino (front nginx, back Python, PostgreSQL)
- `tp/` : les énoncés des TP (un dossier par TP, ajouté dans chaque branche)

## Les branches des TP

Chaque branche part de la précédente : elle contient l'énoncé du TP et l'état de l'application à la fin des TP précédents.
La correction d'un TP est la branche suivante.

| Branche | TP |
|---------|----|
| `tp-01-installation` | Installation du cluster |
| `tp-02-deploiement` | Déploiement de Croustino |
| `tp-03-stockage` | StorageClass et StatefulSet |
| `tp-04-rbac` | Authentification et RBAC |
| `tp-05-capacite` | LimitRange et ResourceQuota |
| `tp-06-helm` | Chart Helm Croustino |
| `tp-07-monitoring` | Prometheus et Grafana |
| `tp-08-logs` | EFK |
| `tp-09-audit` | Audit du cluster |
| `tp-10-harbor` | Registre Harbor |
| `tp-11-cycle-de-vie` | etcd et mise à jour du cluster |
| `solution-finale` | Correction du TP 11 |

Sur le control plane :

```bash
git clone https://github.com/mikou-mouad/ascent-kube-avance.git
cd ascent-kube-avance
git checkout tp-02-deploiement
```

## Les images

Le workflow `.github/workflows/images.yml` publie les images sur `ghcr.io/mikou-mouad` :

| Image | Tags |
|-------|------|
| `croustino-back` | `1.0` |
| `croustino-front` | `1.0` (bandeau marron), `1.1` (bandeau vert, pour le rolling update) |

Pour essayer l'application « comme sur la VM » : `cd app && docker compose up --build`, puis http://localhost:8000.
