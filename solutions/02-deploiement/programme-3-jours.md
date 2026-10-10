# Kubernetes – Avancé : programme sur 3 jours

**Durée :** 3 jours – 21 h · **Format :** distanciel · **Public :** administrateurs, développeurs, architectes

**Rythme d'une journée**

| Demi-journée | Horaires      | Pause         |
|--------------|---------------|---------------|
| Matin        | 9h00 – 12h30  | 10h30 – 10h45 |
| Après-midi   | 13h30 – 17h00 | 15h15 – 15h30 |

**Répartition (hors pauses : 19 h 30)**

| Type        | Durée   | Part   |
|-------------|---------|--------|
| Pratique (TP) | 13 h 30 | **69 %** |
| Théorie (incident + concept) | 4 h 45 | 24 % |
| Accueil, récapitulatifs, quiz, bilan | 1 h 15 | 7 % |

La théorie est volontairement courte (15 à 40 min par chapitre) : on présente l'incident, le concept, et on passe tout de suite au TP.

---

## Le fil rouge : l'histoire de Croustino

**Croustino** est une jeune entreprise qui livre des croissants et des viennoiseries chaudes au petit-déjeuner, à domicile et en entreprise.
Tout se joue entre **6h30 et 9h00** : c'est là que tombent 80 % des commandes.

L'application tient sur **une seule VM** (code dans `app/`) :

```
            ┌──────────────────── VM "prod-croustino" ─────────────────────┐
 clients ──▶│  front (nginx + SPA) ──▶ back (API commandes) ──▶ PostgreSQL │
            └──────────────────────────────────────────────────────────────┘
```

Les personnages :

- **Sophie**, fondatrice : elle veut que les croissants arrivent chauds et que le site ne tombe jamais.
- **Malik**, développeur back : il pousse du code tous les jours, souvent en direct sur la VM.
- **Inès**, admin système : elle gère la VM et commence à manquer de sommeil.

**Principe du cours :** chaque chapitre commence par un **incident** chez Croustino.
On l'analyse ensemble, on présente le **concept Kubernetes** qui y répond, puis on le met en œuvre en **TP** sur l'application Croustino.

| Ch. | Incident chez Croustino | Concept | Module officiel | Branche du TP |
|-----|-------------------------|---------|-----------------|---------------|
| 0 | Chaque mise à jour coupe le site, la VM sature au rush de 7h | Architecture de Kubernetes | Mise à niveau | – |
| 1 | « Il nous faut un vrai cluster » | Installation avec kubeadm | Préparation des TP | `tp-01-installation` |
| 2 | Première migration de l'application | Pod, Deployment, Service, ConfigMap, Secret | Mise à niveau | `tp-02-deploiement` |
| 3 | Le pod PostgreSQL redémarre : les commandes du matin ont disparu | StorageClass, PVC, StatefulSet | Volumes avancés | `tp-03-stockage` |
| 4 | Un stagiaire supprime la prod, tout le monde est admin | Authentification, ServiceAccounts, RBAC | Authentification & autorisation | `tp-04-rbac` |
| 5 | Le service « promos » consomme toute la RAM et la prod tombe à 7h | Requests/limits, LimitRange, ResourceQuota | Gestion de la capacité | `tp-05-capacite` |
| 6 | Ouverture à Lyon : les YAML sont copiés-collés par ville | Charts, values, releases | Helm | `tp-06-helm` |
| 7 | Les clients se plaignent de lenteurs, l'équipe l'apprend sur les réseaux sociaux | Prometheus, Grafana, alertes | Monitoring | `tp-07-monitoring` |
| 8 | Une commande a disparu, mais le pod qui l'a traitée n'existe plus | Logs centralisés, EFK | Gestion des logs | `tp-08-logs` |
| 9 | Le back de prod a été supprimé à 3h du matin. Par qui ? | Politique et analyse d'audit | Audit | `tp-09-audit` |
| 10 | Docker Hub limite les pulls au rush, une faille est trouvée dans une image | Registre privé, scan de vulnérabilités | Harbor | `tp-10-harbor` |
| 11 | Le control plane tombe la veille de l'Épiphanie, la version n'est plus supportée | HA, sauvegarde etcd, mise à jour | Architecture avancée | `tp-11-cycle-de-vie` |

**Les branches :** chaque branche `tp-NN` part de la branche du TP précédent. Elle contient l'énoncé du TP (`tp/NN-*/README.md`) et l'état de l'application à la fin des TP précédents.
La correction du TP NN est donc la branche suivante, et `solution-finale` contient la correction du TP 11.
Un participant bloqué fait `git checkout tp-NN` et repart du bon point de départ.

---

## Jour 1 – De la VM au cluster

**Théorie 1 h 20 · Pratique 4 h 40 · Autre 30 min**

### Matin – Mise à niveau et construction du cluster

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h15   | Accueil | Tour de table (niveau et attentes de chacun), présentation de Croustino |
| 9h15 – 9h45   | Théorie | **Ch. 0 – « Le site tombe à chaque mise à jour »** · Du monolithe sur VM aux conteneurs. Architecture de Kubernetes : control plane (API server, etcd, scheduler, controller-manager), nœuds (kubelet, runtime, kube-proxy), CNI |
| 9h45 – 10h30  | **TP 01** | **Ch. 1 – « Il nous faut un vrai cluster »** · Préparation des 3 nœuds (swap, modules, sysctl, containerd, paquets), vérifications |
| 10h30 – 10h45 | | *Pause* |
| 10h45 – 12h00 | **TP 01** | `kubeadm init`, Calico, `kubeadm join`, tests réseau, snapshot des VM |
| 12h00 – 12h30 | Théorie | **Ch. 2 – Première migration** · Mise à niveau : Pod, Deployment, Service, Namespace, ConfigMap, Secret, probes, manifests YAML et `kubectl` |

### Après-midi – Première migration et premier incident

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 13h30 – 15h15 | **TP 02** | Déploiement guidé de Croustino : namespace, PostgreSQL, back, front, ConfigMap, Secret, NodePort, scaling, rolling update v1.0 → v1.1 |
| 15h15 – 15h30 | | *Pause* |
| 15h30 – 15h50 | Théorie | **Ch. 3 – « Les commandes du matin ont disparu »** · PV/PVC, provisionnement dynamique, StorageClass, StatefulSet |
| 15h50 – 16h45 | **TP 03** | Reproduction de la perte de données, local-path-provisioner, migration de PostgreSQL en StatefulSet |
| 16h45 – 17h00 | Quiz | Quiz du jour 1 · « Journal de Croustino » |

---

## Jour 2 – Croustino grandit

**Théorie 2 h · Pratique 4 h 20 · Autre 10 min**

### Matin – Authentification & autorisation

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h10   | Récap | Récapitulatif du jour 1 |
| 9h10 – 9h50   | Théorie | **Ch. 4 – « Le stagiaire a supprimé la prod »** · Identités (utilisateurs, ServiceAccounts), authentification (X.509, tokens, OIDC, kubeconfig), tokens de ServiceAccount, modes d'autorisation |
| 9h50 – 10h30  | **TP 04** | Création des comptes de Malik, du stagiaire et d'Inès via l'API CertificateSigningRequest, kubeconfigs dédiés |
| 10h30 – 10h45 | | *Pause* |
| 10h45 – 11h05 | Théorie | Administration RBAC : Role, ClusterRole, bindings, rôles intégrés, moindre privilège |
| 11h05 – 12h30 | **TP 04** | Rôles et bindings, ServiceAccount du back, `kubectl auth can-i`, le stagiaire réessaie de supprimer la prod |

### Après-midi – Capacité, packaging et monitoring

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 13h30 – 13h50 | Théorie | **Ch. 5 – « Le service promos a mangé toute la RAM »** · Allocatable, requests/limits, QoS, LimitRange, ResourceQuota |
| 13h50 – 14h40 | **TP 05** | metrics-server, service « promos » gourmand, LimitRange, ResourceQuota, requests/limits sur Croustino |
| 14h40 – 15h00 | Théorie | **Ch. 6 – « On ouvre à Lyon »** · Helm : charts, templates, values, releases, repositories |
| 15h00 – 15h15 | **TP 06** | Création du chart Croustino |
| 15h15 – 15h30 | | *Pause* |
| 15h30 – 16h30 | **TP 06** | Migration de Rennes vers Helm sans perdre les commandes, déploiement de Lyon, upgrade et rollback |
| 16h30 – 16h50 | Théorie | **Ch. 7 – « On l'a appris sur les réseaux sociaux »** · Monitoring : métriques, pull, exporters, Prometheus Operator, Grafana, alertes |
| 16h50 – 17h00 | **TP 07** | Lancement de l'installation de kube-prometheus-stack |

---

## Jour 3 – Exploiter Croustino en production

**Théorie 1 h 25 · Pratique 4 h 30 · Autre 35 min**

### Matin – Monitoring (suite), logs et audit

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h10   | Récap | Récapitulatif et quiz du jour 2 |
| 9h10 – 10h00  | **TP 07** | ServiceMonitor, PromQL, simulation du rush du matin, dashboard Grafana, alerte |
| 10h00 – 10h15 | Théorie | **Ch. 8 – « La commande perdue »** · Logs applicatifs, solutions du marché, modèle EFK |
| 10h15 – 10h30 | **TP 08** | Installation d'ECK (Elasticsearch, Kibana) |
| 10h30 – 10h45 | | *Pause* |
| 10h45 – 11h25 | **TP 08** | Fluent Bit, recherche de la commande perdue dans Kibana |
| 11h25 – 11h40 | Théorie | **Ch. 9 – « Qui a supprimé le back ? »** · Audit : niveaux, politique, backends |
| 11h40 – 12h30 | **TP 09** | Activation de l'audit, incident simulé, analyse avec `jq` |

### Après-midi – Registre, architecture et cycle de vie

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 13h30 – 13h45 | Théorie | **Ch. 10 – « Docker Hub nous bloque au rush »** · Harbor : projets, robots, réplication, scan Trivy |
| 13h45 – 14h35 | **TP 10** | Déploiement de Harbor, copie des images, scan, Croustino tiré depuis Harbor |
| 14h35 – 15h15 | Théorie | **Ch. 11 – « Le control plane est tombé »** · HA (etcd, API server), topologies, best practices, cycle de vie et versions |
| 15h15 – 15h30 | | *Pause* |
| 15h30 – 16h35 | **TP 11** | PodDisruptionBudget, sauvegarde/restauration d'etcd, mise à jour v1.34 → v1.35 |
| 16h35 – 17h00 | Bilan | Épilogue (architecture finale vs VM de départ), QCM final, évaluations |

---

## Gérer les niveaux différents

- **TP 02** : énoncé pas à pas avec des manifests à compléter (`TODO`). Il sert aussi de mise à niveau pratique.
- **Chaque TP** a une partie obligatoire et des **bonus** pour ceux qui finissent en avance.
- **Binômes** possibles : le participant le plus à l'aise explique, l'autre tape les commandes.
- **Rattrapage** : un participant en retard fait `git checkout tp-NN` pour repartir de l'état attendu.

## Préparation du formateur

1. Pousser le dépôt et toutes les branches sur GitHub, le rendre accessible aux participants.
2. Lancer le workflow `images` (onglet Actions) pour publier `croustino-back:1.0`, `croustino-front:1.0` et `croustino-front:1.1` sur `ghcr.io`, puis rendre les paquets publics.
3. Prévoir 3 VM par participant (8 Go de RAM sur les workers : Prometheus, Elasticsearch et Harbor sont gourmands).

## Correspondance avec le programme officiel

| Module officiel                      | Durée officielle | Durée prévue (dont TP) |
|--------------------------------------|------------------|------------------------|
| Mise à niveau, installation, déploiement | –            | 4 h 45 (3 h 45)        |
| Prise en charge des volumes avancés  | 1 h              | 1 h 15 (55 min)        |
| Authentification & autorisation      | 2,5 h            | 3 h 05 (2 h 05)        |
| Gestion de la capacité               | 1,5 h            | 1 h 10 (50 min)        |
| Helm & packaging applicatif          | 1 h              | 1 h 35 (1 h 15)        |
| Monitoring                           | 2 h              | 1 h 20 (1 h)           |
| Gestion des logs                     | 2 h              | 1 h 10 (55 min)        |
| Audit                                | 1 h              | 1 h 05 (50 min)        |
| Harbor & les registres avancés       | 1 h              | 1 h 05 (50 min)        |
| Architecture avancée                 | 2 h              | 1 h 45 (1 h 05)        |
| Accueil, récapitulatifs, quiz, bilan | –                | 1 h 15                 |
| **Total (hors pauses)**              | 14 h             | **19 h 30 (13 h 30)**  |
