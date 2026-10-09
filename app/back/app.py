"""API de commandes Croustino.

Volontairement simple : bibliothèque standard + psycopg, logs JSON sur stdout,
métriques Prometheus écrites à la main sur /metrics.
"""
import json
import os
import signal
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg

VERSION = os.environ.get("APP_VERSION", "1.0")
VILLE = os.environ.get("VILLE", "Rennes")
PORT = int(os.environ.get("PORT", "8080"))
# Au-delà de cette quantité, la fournée ne suffit pas : la commande est rejetée.
STOCK_MAX = int(os.environ.get("STOCK_MAX", "24"))

PRODUITS = [
    {"id": "croissant", "nom": "Croissant", "prix": 1.20},
    {"id": "pain-chocolat", "nom": "Pain au chocolat", "prix": 1.40},
    {"id": "pain-raisins", "nom": "Pain aux raisins", "prix": 1.60},
    {"id": "chausson", "nom": "Chausson aux pommes", "prix": 1.80},
]
IDS_PRODUITS = {p["id"] for p in PRODUITS}

SCHEMA = """
CREATE TABLE IF NOT EXISTS commandes (
    id        TEXT PRIMARY KEY,
    client    TEXT NOT NULL,
    produit   TEXT NOT NULL,
    quantite  INTEGER NOT NULL,
    creee_le  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_verrou = threading.Lock()
_metriques = {
    "commandes": {},          # produit -> nombre
    "rejets": 0,
    "requetes": {},           # (methode, route, code) -> nombre
}


def log(niveau, evenement, **champs):
    ligne = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "niveau": niveau,
        "evenement": evenement,
        "ville": VILLE,
        "pod": socket.gethostname(),
        **champs,
    }
    print(json.dumps(ligne, ensure_ascii=False), flush=True)


def connexion():
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "croustino"),
        user=os.environ.get("DB_USER", "croustino"),
        password=os.environ.get("DB_PASSWORD", ""),
        connect_timeout=3,
    )


def assurer_schema():
    # Pas de cache : si PostgreSQL repart d'un volume vide, la table est recréée.
    with connexion() as cx:
        cx.execute(SCHEMA)


def compter(table, cle):
    with _verrou:
        table[cle] = table.get(cle, 0) + 1


def metriques_texte():
    lignes = [
        "# HELP croustino_info Version de l'API Croustino.",
        "# TYPE croustino_info gauge",
        f'croustino_info{{version="{VERSION}",ville="{VILLE}"}} 1',
        "# HELP croustino_commandes_total Commandes enregistrées, par produit.",
        "# TYPE croustino_commandes_total counter",
    ]
    with _verrou:
        for produit in sorted(IDS_PRODUITS):
            n = _metriques["commandes"].get(produit, 0)
            lignes.append(f'croustino_commandes_total{{produit="{produit}"}} {n}')
        lignes += [
            "# HELP croustino_commandes_rejetees_total Commandes rejetées (fournée insuffisante).",
            "# TYPE croustino_commandes_rejetees_total counter",
            f"croustino_commandes_rejetees_total {_metriques['rejets']}",
            "# HELP croustino_http_requetes_total Requêtes HTTP traitées.",
            "# TYPE croustino_http_requetes_total counter",
        ]
        for (methode, route, code), n in sorted(_metriques["requetes"].items()):
            lignes.append(
                f'croustino_http_requetes_total{{methode="{methode}",route="{route}",code="{code}"}} {n}'
            )
    return "\n".join(lignes) + "\n"


class Handler(BaseHTTPRequestHandler):
    server_version = "croustino-back"

    def log_message(self, *args):  # les logs d'accès passent par log()
        pass

    def repondre(self, code, corps, type_contenu="application/json"):
        if isinstance(corps, (dict, list)):
            corps = json.dumps(corps, ensure_ascii=False)
        donnees = corps.encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{type_contenu}; charset=utf-8")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)
        route = self.path.split("?")[0]
        if route not in ("/healthz", "/readyz", "/metrics"):
            compter(_metriques["requetes"], (self.command, route, str(code)))

    def do_GET(self):
        route = self.path.split("?")[0]
        if route == "/healthz":
            return self.repondre(200, {"statut": "ok"})
        if route == "/readyz":
            try:
                assurer_schema()
                return self.repondre(200, {"statut": "pret"})
            except Exception as e:  # noqa: BLE001
                log("WARN", "base_indisponible", erreur=str(e))
                return self.repondre(503, {"statut": "base indisponible"})
        if route == "/metrics":
            return self.repondre(200, metriques_texte(), "text/plain; version=0.0.4")
        if route == "/api/version":
            return self.repondre(200, {"version": VERSION, "ville": VILLE, "pod": socket.gethostname()})
        if route == "/api/produits":
            return self.repondre(200, PRODUITS)
        if route == "/api/commandes":
            try:
                assurer_schema()
                with connexion() as cx:
                    lignes = cx.execute(
                        "SELECT id, client, produit, quantite, creee_le FROM commandes "
                        "ORDER BY creee_le DESC LIMIT 50"
                    ).fetchall()
            except Exception as e:  # noqa: BLE001
                log("ERROR", "lecture_commandes_impossible", erreur=str(e))
                return self.repondre(503, {"erreur": "base indisponible"})
            return self.repondre(200, [
                {"id": l[0], "client": l[1], "produit": l[2], "quantite": l[3], "creee_le": l[4].isoformat()}
                for l in lignes
            ])
        return self.repondre(404, {"erreur": "introuvable"})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/commandes":
            return self.repondre(404, {"erreur": "introuvable"})
        try:
            longueur = int(self.headers.get("Content-Length", "0"))
            donnees = json.loads(self.rfile.read(longueur) or b"{}")
            client = str(donnees["client"]).strip()
            produit = str(donnees["produit"])
            quantite = int(donnees["quantite"])
            if not client or produit not in IDS_PRODUITS or quantite < 1:
                raise ValueError
        except (KeyError, ValueError, json.JSONDecodeError):
            return self.repondre(400, {"erreur": "commande invalide (client, produit, quantite)"})

        commande_id = uuid.uuid4().hex[:8]
        log("INFO", "commande_recue", commande_id=commande_id, client=client, produit=produit, quantite=quantite)

        if quantite > STOCK_MAX:
            compter_rejet()
            log("ERROR", "commande_rejetee", commande_id=commande_id, client=client, produit=produit,
                quantite=quantite, raison=f"fournée insuffisante (max {STOCK_MAX})")
            return self.repondre(409, {"erreur": "fournée insuffisante", "id": commande_id})

        try:
            assurer_schema()
            with connexion() as cx:
                cx.execute(
                    "INSERT INTO commandes (id, client, produit, quantite) VALUES (%s, %s, %s, %s)",
                    (commande_id, client, produit, quantite),
                )
        except Exception as e:  # noqa: BLE001
            log("ERROR", "enregistrement_impossible", commande_id=commande_id, erreur=str(e))
            return self.repondre(503, {"erreur": "base indisponible", "id": commande_id})

        compter(_metriques["commandes"], produit)
        log("INFO", "commande_enregistree", commande_id=commande_id, client=client, produit=produit, quantite=quantite)
        return self.repondre(201, {"id": commande_id})


def compter_rejet():
    with _verrou:
        _metriques["rejets"] += 1


def main():
    serveur = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    def arreter(signum, _frame):
        log("INFO", "arret", signal=signum)
        threading.Thread(target=serveur.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, arreter)
    signal.signal(signal.SIGINT, arreter)
    log("INFO", "demarrage", version=VERSION, port=PORT, stock_max=STOCK_MAX)
    serveur.serve_forever()


if __name__ == "__main__":
    main()
