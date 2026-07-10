"""
ia.py
Intégration d'une API d'IA générative gratuite (Groq — https://console.groq.com)
pour assister le producteur dans la rédaction de la description de sa récolte.

Groq propose un accès gratuit (sans carte bancaire) à des modèles Llama en
inférence très rapide, compatible avec le format d'API OpenAI. Aucune donnée
n'est envoyée si aucune clé n'est configurée : la fonctionnalité se dégrade
alors proprement (message informatif, saisie manuelle de la description).
"""

import os
import requests

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # modèle gratuit, rapide, suffisant pour une courte description

TIMEOUT_SECONDES = 15


def ia_disponible():
    return bool(GROQ_API_KEY)


def generer_description(libelle_produit, quantite, mots_cles=""):
    """
    Appelle l'API Groq (gratuite) pour générer une courte description commerciale
    de la récolte, en français, à partir du nom du produit, de la quantité et
    de mots-clés optionnels fournis par le producteur.

    Retourne (description: str, erreur: str|None).
    """
    if not ia_disponible():
        return None, "Aucune clé GROQ_API_KEY configurée sur le serveur."

    prompt = (
        "Tu rédiges une courte description commerciale (3 phrases maximum, "
        "en français, sans emoji, sans markdown) pour une annonce de vente "
        "agricole en gros destinée à des collecteurs et transporteurs.\n"
        f"Produit : {libelle_produit}\n"
        f"Quantité disponible : {quantite} kg\n"
        + (f"Informations complémentaires données par le producteur : {mots_cles}\n" if mots_cles else "")
        + "Mets en valeur la fraîcheur, la qualité et la disponibilité pour un enlèvement rapide."
    )

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "Tu es un assistant qui aide des producteurs agricoles malgaches à décrire leurs récoltes pour les vendre."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
                "max_tokens": 200,
            },
            timeout=TIMEOUT_SECONDES,
        )
        response.raise_for_status()
        data = response.json()
        texte = data["choices"][0]["message"]["content"].strip()
        return texte, None
    except requests.exceptions.RequestException as exc:
        return None, f"Erreur lors de l'appel à l'IA : {exc}"
    except (KeyError, IndexError, ValueError):
        return None, "Réponse inattendue de l'API IA."


def generer_avis_partenaires(nom_utilisateur, role_utilisateur, partenaires):
    """
    Fonctionnalité "Agent IA de mise en relation".
    À partir du classement déterministe calculé par scoring.meilleurs_partenaires(),
    demande à l'IA de rédiger un court avis (2-4 phrases) expliquant, en français,
    pourquoi contacter les meilleurs partenaires suggérés.

    Retourne (avis: str, erreur: str|None).
    """
    if not ia_disponible():
        return None, "Aucune clé GROQ_API_KEY configurée sur le serveur."

    lignes = []
    for role, liste in partenaires.items():
        if not liste:
            lignes.append(f"- Aucun {role.lower()} disponible à proximité pour le moment.")
            continue
        for c in liste[:3]:
            dispo = "disponible" if c.get("est_disponible") else "indisponible"
            lignes.append(f"- {role} : {c['nom_complet']}, à {c['distance_km']} km, {dispo}.")

    prompt = (
        f"Un utilisateur nommé {nom_utilisateur}, de profil {role_utilisateur}, "
        "utilise une application de mise en relation agricole à Madagascar.\n"
        "Voici les partenaires potentiels détectés automatiquement par le système "
        "(triés par disponibilité puis proximité) :\n"
        + "\n".join(lignes)
        + "\n\nRédige un avis court (4 phrases maximum, en français, sans markdown, sans emoji) "
          "recommandant avec qui entrer en contact en priorité et pourquoi, "
          "en te basant uniquement sur la disponibilité et la distance indiquées."
    )

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "Tu es l'agent IA d'AgriMarketFlow, tu aides producteurs, collecteurs et transporteurs malgaches à choisir avec qui collaborer."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.5,
                "max_tokens": 220,
            },
            timeout=TIMEOUT_SECONDES,
        )
        response.raise_for_status()
        data = response.json()
        texte = data["choices"][0]["message"]["content"].strip()
        return texte, None
    except requests.exceptions.RequestException as exc:
        return None, f"Erreur lors de l'appel à l'IA : {exc}"
    except (KeyError, IndexError, ValueError):
        return None, "Réponse inattendue de l'API IA."
