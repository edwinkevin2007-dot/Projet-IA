"""
app.py
AgriMarketFlow AI — application Flask
Connecte producteurs, collecteurs et transporteurs (cf. Cahier des Charges, Sujet 7).
"""

from functools import wraps
from datetime import datetime
import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_connection, init_db
from scoring import distance_km, prestataires_proches, calculer_scores, meilleurs_partenaires
import ia
import email_verif

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# Upload des photos/vidéos de récolte
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
EXT_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
EXT_VIDEOS = {"mp4", "webm", "mov", "m4v"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 Mo par requête
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PRESTATAIRE_PROFILS = ("Collecteur", "Transporteur")


def extension_autorisee(nom_fichier, extensions_valides):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in extensions_valides


def enregistrer_medias(id_recolte, fichiers_images, fichiers_videos):
    """Sauvegarde les fichiers uploadés sur disque et les référence en base (RECOLTE_MEDIA)."""
    conn = get_connection()
    ordre = 0
    dossier_recolte = os.path.join(app.config["UPLOAD_FOLDER"], "recoltes", str(id_recolte))
    os.makedirs(dossier_recolte, exist_ok=True)

    for f in fichiers_images:
        if f and f.filename and extension_autorisee(f.filename, EXT_IMAGES):
            nom = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
            f.save(os.path.join(dossier_recolte, nom))
            chemin_relatif = f"uploads/recoltes/{id_recolte}/{nom}"
            conn.execute(
                "INSERT INTO RECOLTE_MEDIA (id_recolte, type_media, chemin, ordre) VALUES (?,?,?,?)",
                (id_recolte, "image", chemin_relatif, ordre),
            )
            ordre += 1

    for f in fichiers_videos:
        if f and f.filename and extension_autorisee(f.filename, EXT_VIDEOS):
            nom = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
            f.save(os.path.join(dossier_recolte, nom))
            chemin_relatif = f"uploads/recoltes/{id_recolte}/{nom}"
            conn.execute(
                "INSERT INTO RECOLTE_MEDIA (id_recolte, type_media, chemin, ordre) VALUES (?,?,?,?)",
                (id_recolte, "video", chemin_relatif, ordre),
            )
            ordre += 1

    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("connexion"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("type_profil") not in roles:
                flash("Cette page n'est pas accessible pour votre profil.", "danger")
                return redirect(url_for("accueil"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def current_user():
    if "user_id" not in session:
        return None
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM UTILISATEUR WHERE id_utilisateur = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return user


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.context_processor
def inject_ia_status():
    return {"ia_disponible": ia.ia_disponible()}


# --------------------------------------------------------------------------- #
# Authentification / gestion des profils
# --------------------------------------------------------------------------- #

@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        nom = request.form["nom_complet"].strip()
        contact = request.form["contact"].strip()
        mdp = request.form["mot_de_passe"]
        type_profil = request.form["type_profil"]
        latitude = float(request.form["latitude"])
        longitude = float(request.form["longitude"])

        conn = get_connection()
        existe = conn.execute(
            "SELECT 1 FROM UTILISATEUR WHERE contact = ?", (contact,)
        ).fetchone()
        if existe:
            flash("Un compte existe déjà avec ce contact.", "danger")
            conn.close()
            return redirect(url_for("inscription"))

        if email_verif.ressemble_a_un_email(contact):
            valide, message = email_verif.verifier_email(contact)
            if not valide:
                flash(message, "danger")
                conn.close()
                return redirect(url_for("inscription"))
            if message == "verification_impossible":
                flash(
                    "Le domaine de l'email n'a pas pu être vérifié (pas de connexion sortante) — "
                    "compte créé quand même.",
                    "warning",
                )

        conn.execute(
            "INSERT INTO UTILISATEUR (nom_complet, contact, mot_de_passe, type_profil, "
            "latitude, longitude, est_disponible) VALUES (?,?,?,?,?,?,1)",
            (nom, contact, generate_password_hash(mdp), type_profil, latitude, longitude),
        )
        conn.commit()
        conn.close()
        flash("Compte créé avec succès. Vous pouvez vous connecter.", "success")
        return redirect(url_for("connexion"))

    return render_template("inscription.html")


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        contact = request.form["contact"].strip()
        mdp = request.form["mot_de_passe"]

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM UTILISATEUR WHERE contact = ?", (contact,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["mot_de_passe"], mdp):
            session["user_id"] = user["id_utilisateur"]
            session["type_profil"] = user["type_profil"]
            session["nom_complet"] = user["nom_complet"]
            flash(f"Bienvenue, {user['nom_complet']} !", "success")
            if user["type_profil"] == "Producteur":
                return redirect(url_for("producteur_dashboard"))
            return redirect(url_for("prestataire_dashboard"))

        flash("Identifiants incorrects.", "danger")
        return redirect(url_for("connexion"))

    return render_template("connexion.html")


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    flash("Vous êtes déconnecté(e).", "info")
    return redirect(url_for("accueil"))


@app.route("/disponibilite/toggle", methods=["POST"])
@login_required
@role_required(*PRESTATAIRE_PROFILS)
def toggle_disponibilite():
    conn = get_connection()
    user = conn.execute(
        "SELECT est_disponible FROM UTILISATEUR WHERE id_utilisateur = ?", (session["user_id"],)
    ).fetchone()
    nouveau = 0 if user["est_disponible"] else 1
    conn.execute(
        "UPDATE UTILISATEUR SET est_disponible = ? WHERE id_utilisateur = ?",
        (nouveau, session["user_id"]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("prestataire_dashboard"))


# --------------------------------------------------------------------------- #
# Espace Producteur
# --------------------------------------------------------------------------- #

@app.route("/producteur")
@login_required
@role_required("Producteur")
def producteur_dashboard():
    conn = get_connection()
    recoltes = conn.execute(
        "SELECT * FROM RECOLTE WHERE id_utilisateur_producteur = ? ORDER BY date_publication DESC",
        (session["user_id"],),
    ).fetchall()
    recoltes = [dict(r, vignette=_premiere_vignette(conn, r["id_recolte"])) for r in recoltes]
    conn.close()
    return render_template("producteur_dashboard.html", recoltes=recoltes)


def _premiere_vignette(conn, id_recolte):
    row = conn.execute(
        "SELECT chemin FROM RECOLTE_MEDIA WHERE id_recolte = ? AND type_media = 'image' "
        "ORDER BY ordre LIMIT 1", (id_recolte,)
    ).fetchone()
    return row["chemin"] if row else None


@app.route("/recolte/nouvelle", methods=["GET", "POST"])
@login_required
@role_required("Producteur")
def nouvelle_recolte():
    if request.method == "POST":
        libelle = request.form["libelle_produit"].strip()
        description = request.form.get("description", "").strip()
        quantite = float(request.form["quantite"])
        latitude = float(request.form["latitude"])
        longitude = float(request.form["longitude"])

        conn = get_connection()
        conn.execute(
            "INSERT INTO RECOLTE (libelle_produit, description, quantite, date_publication, "
            "latitude_origine, longitude_origine, statut, id_utilisateur_producteur) "
            "VALUES (?,?,?,?,?,?,'En attente',?)",
            (libelle, description, quantite, datetime.now().isoformat(timespec="seconds"),
             latitude, longitude, session["user_id"]),
        )
        conn.commit()
        recolte_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        conn.close()

        images = request.files.getlist("images")
        videos = request.files.getlist("videos")
        enregistrer_medias(recolte_id, images, videos)

        flash("Récolte publiée. Les prestataires à proximité vont être suggérés.", "success")
        return redirect(url_for("detail_recolte", recolte_id=recolte_id))

    user = current_user()
    return render_template("nouvelle_recolte.html", user=user)


@app.route("/api/ia/description", methods=["POST"])
@login_required
@role_required("Producteur")
def api_generer_description():
    data = request.get_json(force=True, silent=True) or {}
    libelle = data.get("libelle_produit", "").strip()
    quantite = data.get("quantite", "")
    mots_cles = data.get("mots_cles", "").strip()

    if not libelle:
        return jsonify({"erreur": "Indiquez d'abord le nom du produit."}), 400

    description, erreur = ia.generer_description(libelle, quantite, mots_cles)
    if erreur:
        return jsonify({"erreur": erreur}), 503
    return jsonify({"description": description})


@app.route("/recolte/<int:recolte_id>")
@login_required
def detail_recolte(recolte_id):
    conn = get_connection()
    recolte = conn.execute(
        "SELECT * FROM RECOLTE WHERE id_recolte = ?", (recolte_id,)
    ).fetchone()
    if not recolte:
        conn.close()
        flash("Récolte introuvable.", "danger")
        return redirect(url_for("accueil"))

    # Suggestion automatique de prestataires à proximité (Matching local)
    prestataires = conn.execute(
        "SELECT * FROM UTILISATEUR WHERE type_profil IN ('Collecteur','Transporteur')"
    ).fetchall()
    suggestions = prestataires_proches(recolte, prestataires)

    # Offres reçues, enrichies de la distance et passées au moteur de scoring
    offres_brutes = conn.execute(
        """SELECT OFFRE.*, UTILISATEUR.nom_complet, UTILISATEUR.type_profil,
                  UTILISATEUR.latitude, UTILISATEUR.longitude, UTILISATEUR.est_disponible
           FROM OFFRE
           JOIN UTILISATEUR ON UTILISATEUR.id_utilisateur = OFFRE.id_utilisateur_prestataire
           WHERE OFFRE.id_recolte = ?""",
        (recolte_id,),
    ).fetchall()

    offres_contexte = []
    for o in offres_brutes:
        d = distance_km(recolte["latitude_origine"], recolte["longitude_origine"],
                         o["latitude"], o["longitude"])
        offres_contexte.append({**dict(o), "distance_km": round(d, 2)})

    offres_scorees = calculer_scores(offres_contexte)

    # Persiste le score calculé (traçabilité, cf. champ score_calcule du MCD)
    for o in offres_scorees:
        conn.execute("UPDATE OFFRE SET score_calcule = ? WHERE id_offre = ?",
                     (o["score"], o["id_offre"]))
    conn.commit()

    est_proprietaire = (session.get("user_id") == recolte["id_utilisateur_producteur"])

    medias = conn.execute(
        "SELECT * FROM RECOLTE_MEDIA WHERE id_recolte = ? ORDER BY ordre", (recolte_id,)
    ).fetchall()
    images = [m for m in medias if m["type_media"] == "image"]
    videos = [m for m in medias if m["type_media"] == "video"]

    conn.close()

    # Payload pour la carte Google Maps : récolte + prestataires suggérés (avec score si offre soumise)
    scores_par_utilisateur = {o["id_utilisateur_prestataire"]: o["score"] for o in offres_scorees}
    map_payload = {
        "recolte": {
            "libelle": recolte["libelle_produit"],
            "quantite": recolte["quantite"],
            "lat": recolte["latitude_origine"],
            "lon": recolte["longitude_origine"],
        },
        "prestataires": [
            {
                "nom": s["nom_complet"],
                "type": s["type_profil"],
                "lat": s["latitude"],
                "lon": s["longitude"],
                "distance_km": s["distance_km"],
                "disponible": bool(s["est_disponible"]),
                "score": scores_par_utilisateur.get(s["id_utilisateur"]),
            }
            for s in suggestions
        ],
    }

    return render_template(
        "recolte_detail.html",
        recolte=recolte,
        suggestions=suggestions,
        offres=offres_scorees,
        est_proprietaire=est_proprietaire,
        map_payload=map_payload,
        images=images,
        videos=videos,
    )


@app.route("/offre/<int:offre_id>/valider", methods=["POST"])
@login_required
@role_required("Producteur")
def valider_offre(offre_id):
    conn = get_connection()
    offre = conn.execute("SELECT * FROM OFFRE WHERE id_offre = ?", (offre_id,)).fetchone()
    recolte = conn.execute(
        "SELECT * FROM RECOLTE WHERE id_recolte = ?", (offre["id_recolte"],)
    ).fetchone()

    if recolte["id_utilisateur_producteur"] != session["user_id"]:
        conn.close()
        flash("Action non autorisée.", "danger")
        return redirect(url_for("accueil"))

    # Validation et Suivi : accepte l'offre, refuse les autres, ouvre la transaction
    conn.execute("UPDATE OFFRE SET statut = 'Acceptée' WHERE id_offre = ?", (offre_id,))
    conn.execute(
        "UPDATE OFFRE SET statut = 'Refusée' WHERE id_recolte = ? AND id_offre != ?",
        (offre["id_recolte"], offre_id),
    )
    conn.execute(
        "UPDATE RECOLTE SET statut = 'En cours' WHERE id_recolte = ?", (offre["id_recolte"],)
    )
    conn.execute(
        "INSERT INTO \"TRANSACTION\" (date_validation, statut_livraison, id_recolte, id_offre) "
        "VALUES (?, 'En préparation', ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), offre["id_recolte"], offre_id),
    )
    conn.commit()
    conn.close()
    flash("Offre validée. Le suivi de la transaction est lancé.", "success")
    return redirect(url_for("detail_recolte", recolte_id=recolte["id_recolte"]))


# --------------------------------------------------------------------------- #
# Espace Collecteur / Transporteur
# --------------------------------------------------------------------------- #

@app.route("/prestataire")
@login_required
@role_required(*PRESTATAIRE_PROFILS)
def prestataire_dashboard():
    conn = get_connection()
    user = current_user()
    recoltes = conn.execute(
        "SELECT * FROM RECOLTE WHERE statut = 'En attente' ORDER BY date_publication DESC"
    ).fetchall()
    recoltes = [dict(r, vignette=_premiere_vignette(conn, r["id_recolte"])) for r in recoltes]

    proches = prestataires_proches(
        {"latitude_origine": user["latitude"], "longitude_origine": user["longitude"]},
        [dict(r, latitude=r["latitude_origine"], longitude=r["longitude_origine"]) for r in recoltes],
    )
    mes_offres = conn.execute(
        """SELECT OFFRE.*, RECOLTE.libelle_produit
           FROM OFFRE JOIN RECOLTE ON RECOLTE.id_recolte = OFFRE.id_recolte
           WHERE OFFRE.id_utilisateur_prestataire = ?
           ORDER BY OFFRE.date_soumission DESC""",
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "prestataire_dashboard.html", recoltes_proches=proches, mes_offres=mes_offres, user=user
    )


@app.route("/recolte/<int:recolte_id>/offre", methods=["POST"])
@login_required
@role_required(*PRESTATAIRE_PROFILS)
def soumettre_offre(recolte_id):
    prix = float(request.form["prix_propose"])
    conn = get_connection()
    conn.execute(
        "INSERT INTO OFFRE (prix_propose, date_soumission, statut, "
        "id_utilisateur_prestataire, id_recolte) VALUES (?,?,'En attente',?,?)",
        (prix, datetime.now().isoformat(timespec="seconds"), session["user_id"], recolte_id),
    )
    conn.commit()
    conn.close()
    flash("Offre envoyée au producteur.", "success")
    return redirect(url_for("prestataire_dashboard"))


@app.route("/assistant")
@login_required
def assistant_ia():
    user = current_user()
    conn = get_connection()
    tous = conn.execute(
        "SELECT * FROM UTILISATEUR WHERE id_utilisateur != ?", (user["id_utilisateur"],)
    ).fetchall()
    conn.close()

    partenaires = meilleurs_partenaires(user, tous)

    avis_ia, erreur_ia = (None, None)
    if request.args.get("generer") == "1":
        avis_ia, erreur_ia = ia.generer_avis_partenaires(
            user["nom_complet"], user["type_profil"], partenaires
        )

    return render_template(
        "assistant.html", partenaires=partenaires, avis_ia=avis_ia, erreur_ia=erreur_ia, user=user
    )


@app.route("/api/ia/diagnostic")
@login_required
def api_diagnostic_ia():
    return jsonify(ia.tester_cle())


# --------------------------------------------------------------------------- #
# API REST (bonus : consommable par un client externe / bibliothèque requests)
# --------------------------------------------------------------------------- #

@app.route("/api/recoltes", methods=["GET"])
def api_recoltes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM RECOLTE ORDER BY date_publication DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/recolte/<int:recolte_id>/suggestions", methods=["GET"])
def api_suggestions(recolte_id):
    conn = get_connection()
    recolte = conn.execute("SELECT * FROM RECOLTE WHERE id_recolte = ?", (recolte_id,)).fetchone()
    if not recolte:
        conn.close()
        return jsonify({"erreur": "Récolte introuvable"}), 404
    prestataires = conn.execute(
        "SELECT * FROM UTILISATEUR WHERE type_profil IN ('Collecteur','Transporteur')"
    ).fetchall()
    conn.close()
    return jsonify(prestataires_proches(recolte, prestataires))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
