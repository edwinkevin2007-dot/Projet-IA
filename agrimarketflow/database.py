"""
database.py
Couche d'accès aux données pour AgriMarketFlow AI.
Implémente le MLD défini dans le cahier des charges (section 5.2) avec SQLite.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "agrimarketflow.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS UTILISATEUR (
    id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_complet     TEXT NOT NULL,
    contact         TEXT NOT NULL UNIQUE,
    mot_de_passe    TEXT NOT NULL,
    type_profil     TEXT NOT NULL CHECK (type_profil IN ('Producteur','Collecteur','Transporteur')),
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    est_disponible  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS RECOLTE (
    id_recolte              INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle_produit         TEXT NOT NULL,
    description              TEXT DEFAULT '',
    quantite                REAL NOT NULL,
    date_publication         TEXT NOT NULL,
    latitude_origine        REAL NOT NULL,
    longitude_origine       REAL NOT NULL,
    statut                  TEXT NOT NULL DEFAULT 'En attente'
                             CHECK (statut IN ('En attente','En cours','Cloturée')),
    id_utilisateur_producteur INTEGER NOT NULL,
    FOREIGN KEY (id_utilisateur_producteur) REFERENCES UTILISATEUR(id_utilisateur)
);

CREATE TABLE IF NOT EXISTS RECOLTE_MEDIA (
    id_media    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_recolte  INTEGER NOT NULL,
    type_media  TEXT NOT NULL CHECK (type_media IN ('image','video')),
    chemin      TEXT NOT NULL,
    ordre       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (id_recolte) REFERENCES RECOLTE(id_recolte)
);

CREATE TABLE IF NOT EXISTS OFFRE (
    id_offre                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prix_propose               REAL NOT NULL,
    date_soumission             TEXT NOT NULL,
    score_calcule               REAL,
    statut                     TEXT NOT NULL DEFAULT 'En attente'
                                CHECK (statut IN ('En attente','Acceptée','Refusée')),
    id_utilisateur_prestataire INTEGER NOT NULL,
    id_recolte                 INTEGER NOT NULL,
    FOREIGN KEY (id_utilisateur_prestataire) REFERENCES UTILISATEUR(id_utilisateur),
    FOREIGN KEY (id_recolte) REFERENCES RECOLTE(id_recolte)
);

CREATE TABLE IF NOT EXISTS "TRANSACTION" (
    id_transaction   INTEGER PRIMARY KEY AUTOINCREMENT,
    date_validation  TEXT NOT NULL,
    statut_livraison TEXT NOT NULL DEFAULT 'En préparation',
    id_recolte       INTEGER NOT NULL,
    id_offre         INTEGER NOT NULL,
    FOREIGN KEY (id_recolte) REFERENCES RECOLTE(id_recolte),
    FOREIGN KEY (id_offre) REFERENCES OFFRE(id_offre)
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed=True):
    """Crée les tables si nécessaire et insère quelques données de démonstration."""
    conn = get_connection()
    conn.executescript(SCHEMA)

    # Migration légère pour les bases créées avant l'ajout de la description produit.
    colonnes = [r["name"] for r in conn.execute("PRAGMA table_info(RECOLTE)")]
    if "description" not in colonnes:
        conn.execute("ALTER TABLE RECOLTE ADD COLUMN description TEXT DEFAULT ''")

    conn.commit()

    if seed:
        count = conn.execute("SELECT COUNT(*) AS n FROM UTILISATEUR").fetchone()["n"]
        if count == 0:
            _seed_demo_data(conn)

    conn.close()


def _seed_demo_data(conn):
    """Jeu de données de démonstration autour d'Antananarivo / Antsirabe."""
    from werkzeug.security import generate_password_hash

    utilisateurs = [
        ("Rakoto Jean",      "rakoto@mail.mg",   "Producteur",   -18.8792, 47.5079, 1),
        ("Rasoa Marie",      "rasoa@mail.mg",    "Producteur",   -19.8667, 47.0333, 1),
        ("Andria Collect",   "andria@mail.mg",   "Collecteur",   -18.9100, 47.5250, 1),
        ("Rabe Négoce",      "rabe@mail.mg",     "Collecteur",   -19.8500, 47.0500, 0),
        ("Solo Transport",   "solo@mail.mg",     "Transporteur", -18.8900, 47.5100, 1),
        ("Fara Logistique",  "fara@mail.mg",     "Transporteur", -19.8600, 47.0400, 1),
    ]
    pwd = generate_password_hash("password123")
    for nom, contact, profil, lat, lon, dispo in utilisateurs:
        conn.execute(
            "INSERT INTO UTILISATEUR (nom_complet, contact, mot_de_passe, type_profil, "
            "latitude, longitude, est_disponible) VALUES (?,?,?,?,?,?,?)",
            (nom, contact, pwd, profil, lat, lon, dispo),
        )
    conn.commit()

    conn.execute(
        "INSERT INTO RECOLTE (libelle_produit, quantite, date_publication, "
        "latitude_origine, longitude_origine, statut, id_utilisateur_producteur) "
        "VALUES ('Riz Vary', 500, datetime('now'), -18.8792, 47.5079, 'En attente', 1)"
    )
    conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Base initialisée : {DB_PATH}")
