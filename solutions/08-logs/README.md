# Correction du TP 08 – Gestion des logs

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `README.md`
- `programme-3-jours.md`

Pour les comparer à votre travail : `diff -r solutions/08-logs/k8s k8s` (ou `helm`).

- **Où sont les logs :** le runtime écrit stdout/stderr de chaque conteneur dans `/var/log/pods/<namespace>_<pod>_<uid>/<conteneur>/`. `/var/log/containers/` contient des liens vers ces fichiers. Ils sont supprimés avec le pod (et tournés au-delà de 10 Mo par défaut).
- **Format du back :** une ligne JSON par événement (`niveau`, `evenement`, `commande_id`, `client`…).
- **Objets créés par ECK :** StatefulSet `logs-es-default`, Services `logs-es-http` / `logs-kb-http`, Secrets de certificats TLS, PVC `elasticsearch-data-logs-es-default-0`. Mot de passe : Secret `logs-es-elastic-user`.
- **DaemonSet :** un collecteur par nœud lit les fichiers locaux. Pas de pod sur le control plane : il porte le taint `node-role.kubernetes.io/control-plane:NoSchedule` et le chart n'a pas de tolérance.
- **Enquête :** requête `client : "Mme Lebrun"` → deux événements, `commande_recue` puis `commande_rejetee` (`niveau: ERROR`), avec la même `commande_id`, le nom du pod (`kubernetes.pod_name`, aujourd'hui supprimé) et la raison : **fournée insuffisante (max 24)**. Elle avait commandé 30 croissants.
- **JSON :** chaque information devient un champ filtrable et agrégable, sans expressions régulières fragiles.
- **Elasticsearch indisponible :** Fluent Bit garde les données en mémoire et réessaie (`Retry_Limit False`). Au-delà de sa mémoire tampon, il perd des logs, sauf avec un tampon sur disque (`storage.type filesystem`). Les fichiers sur les nœuds servent aussi de tampon tant qu'ils ne sont pas tournés.
- **Conservation :** politique ILM d'Elasticsearch (suppression des index après N jours), un index par jour (`Logstash_Format`), taille des volumes, et filtrage à la source des logs inutiles.
