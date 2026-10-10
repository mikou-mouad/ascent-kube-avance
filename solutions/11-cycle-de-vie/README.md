# Correction du TP 11 – Architecture avancée et cycle de vie

## YAML prêts à l'emploi

Pour ceux qui n'ont pas réussi à les écrire, dans ce dossier :

- `etcd-restauration.md` : remettre etcd sur les données restaurées sans modifier `etcd.yaml`, pourquoi, et comment réparer si le `hostPath` a été changé

Le **chart complet corrigé** est dans `solutions/11-cycle-de-vie/helm/croustino/`. On peut l'installer tel quel :

```bash
helm upgrade croustino solutions/11-cycle-de-vie/helm/croustino -n croustino -f solutions/11-cycle-de-vie/helm/croustino/values-rennes.yaml
```

Pour voir ce qui change par rapport à votre chart : `diff -r solutions/11-cycle-de-vie/helm helm`.

PodDisruptionBudgets : `helm/croustino/templates/pdb.yaml`.

- **PDB avec un seul réplica :** `maxUnavailable: 1` ne protège rien, et `minAvailable: 1` empêcherait toute éviction : le drain resterait bloqué indéfiniment. Il faut d'abord plusieurs réplicas.
- **Sauvegarde sur le control plane :** non. Si le disque ou la VM est perdu, la sauvegarde l'est aussi. Il faut la copier ailleurs (stockage objet, autre site), la chiffrer, et tester la restauration régulièrement.
- **Objets créés après la sauvegarde :** ils ont disparu de l'API. Les pods qui tournent encore sur les nœuds sont arrêtés ou réconciliés par le kubelet et les contrôleurs. Une restauration d'etcd est une machine à remonter le temps pour **tout** le cluster : on la réserve aux catastrophes. Pour un namespace supprimé, on préfère redéployer depuis Git / Helm, ou un outil de sauvegarde applicative comme Velero.
- **Erreurs pendant le drain :** PostgreSQL n'a qu'un réplica et son volume local-path est lié à un nœud. Pendant le drain de ce nœud, le pod `postgres-0` est évincé et reste `Pending` jusqu'au `uncordon` : le back n'est plus prêt et l'API répond en erreur. Solutions : stockage répliqué (Longhorn, Ceph) ou base répliquée avec bascule (opérateur CloudNativePG), ou base managée.
- **Single points of failure et solutions :**
  - control plane unique (API server, etcd) → 3 control planes derrière un load balancer, etcd à 3 membres ;
  - PostgreSQL à un réplica sur stockage local → réplication et stockage distribué ;
  - Harbor sans HA → stockage objet, réplicas, réplication vers un second registre ;
  - accès par NodePort sur l'IP d'un nœud → load balancer ou Ingress avec IP virtuelle ;
  - sauvegardes d'etcd locales → sauvegardes externalisées et testées.
- **Une mineure à la fois :** la politique de compatibilité de Kubernetes (version skew) n'autorise qu'une mineure d'écart entre kubeadm et le cluster. Les migrations (APIs dépréciées, format des données d'etcd, configuration des composants) sont prévues pour s'enchaîner version par version.
