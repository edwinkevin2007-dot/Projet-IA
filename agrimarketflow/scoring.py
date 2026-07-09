"""
scoring.py
Moteur de recommandation : calcule la distance géographique (Haversine) et
un score pondéré multicritères (prix, distance, disponibilité) tel que
spécifié en section 3 et 4 du cahier des charges.
"""

import math

# Pondérations par défaut du moteur de scoring — ajustables sans toucher au reste du code.
POIDS = {
    "prix": 0.4,
    "distance": 0.4,
    "disponibilite": 0.2,
}

RAYON_TERRE_KM = 6371.0
RAYON_SUGGESTION_KM = 100  # rayon de "proximité" pour le matching automatique


def distance_km(lat1, lon1, lat2, lon2):
    """Distance orthodromique (grand cercle) entre deux points GPS, en km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return RAYON_TERRE_KM * c


def prestataires_proches(recolte, prestataires, rayon_km=RAYON_SUGGESTION_KM):
    """
    Fonctionnalité "Suggestion automatique (Matching local)".
    Retourne les prestataires (collecteurs/transporteurs) triés par distance
    croissante, dans un rayon donné autour de la récolte.
    """
    resultats = []
    for p in prestataires:
        d = distance_km(
            recolte["latitude_origine"], recolte["longitude_origine"],
            p["latitude"], p["longitude"],
        )
        if d <= rayon_km:
            resultats.append({**dict(p), "distance_km": round(d, 2)})
    resultats.sort(key=lambda x: x["distance_km"])
    return resultats


def _normaliser(valeur, minimum, maximum, inverser=False):
    """Ramène une valeur sur [0, 1]. Si inverser=True, une valeur plus basse donne un score plus haut."""
    if maximum == minimum:
        return 1.0
    n = (valeur - minimum) / (maximum - minimum)
    n = max(0.0, min(1.0, n))
    return 1 - n if inverser else n


def calculer_scores(offres_avec_contexte, poids=None):
    """
    Fonctionnalité "Comparaison et Scoring".
    Prend une liste de dicts contenant au minimum :
        prix_propose, distance_km, est_disponible
    et renvoie la même liste enrichie d'un champ 'score' (0 à 100),
    triée du meilleur au moins bon score.

    Le score est une moyenne pondérée normalisée :
      - prix bas  => meilleur score
      - distance courte => meilleur score
      - disponibilité immédiate => meilleur score
    """
    poids = poids or POIDS
    if not offres_avec_contexte:
        return []

    prix_list = [o["prix_propose"] for o in offres_avec_contexte]
    dist_list = [o["distance_km"] for o in offres_avec_contexte]
    prix_min, prix_max = min(prix_list), max(prix_list)
    dist_min, dist_max = min(dist_list), max(dist_list)

    resultat = []
    for o in offres_avec_contexte:
        score_prix = _normaliser(o["prix_propose"], prix_min, prix_max, inverser=True)
        score_distance = _normaliser(o["distance_km"], dist_min, dist_max, inverser=True)
        score_dispo = 1.0 if o.get("est_disponible") else 0.0

        score_final = (
            score_prix * poids["prix"]
            + score_distance * poids["distance"]
            + score_dispo * poids["disponibilite"]
        ) * 100

        resultat.append({
            **o,
            "score": round(score_final, 1),
            "detail": {
                "prix": round(score_prix * 100),
                "distance": round(score_distance * 100),
                "disponibilite": round(score_dispo * 100),
            },
        })

    resultat.sort(key=lambda x: x["score"], reverse=True)
    return resultat
