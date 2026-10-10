# Correction du TP 01 – Installation du cluster

1. **Swap :** le kubelet calcule les ressources disponibles et les évictions à partir de la mémoire physique. Avec du swap, ces calculs deviennent faux, il refuse donc de démarrer par défaut (le support du swap existe mais doit être configuré explicitement).
2. **br_netfilter / ip_forward :** `br_netfilter` fait passer le trafic des bridges Linux par iptables (nécessaire à kube-proxy et aux NetworkPolicies). `ip_forward` autorise le nœud à router les paquets entre les interfaces des pods.
3. **Driver cgroup :** si containerd et le kubelet ne gèrent pas les cgroups de la même façon, deux gestionnaires se disputent les ressources. Le kubelet devient instable sous charge (pods tués, nœud qui flappe).
4. **apt-mark hold :** une mise à jour système (`apt upgrade`) ne doit jamais changer la version de Kubernetes. Les montées de version se font avec kubeadm, une mineure à la fois (TP 11).
5. **Static pods :** kube-apiserver, etcd, kube-scheduler, kube-controller-manager. Le kubelet les démarre directement depuis `/etc/kubernetes/manifests`, sans passer par l'API server.
6. **NotReady :** aucun CNI n'est installé, le kubelet signale que le réseau des pods n'est pas prêt.
7. **Certificats :** `/etc/kubernetes/pki`. Les certificats des composants sont valides 1 an, l'autorité de certification 10 ans. `kubeadm upgrade` les renouvelle.
8. **calico-node :** 3, un par nœud : c'est un DaemonSet.
9. **Token :** 24 heures par défaut (`kubeadm token list`).
