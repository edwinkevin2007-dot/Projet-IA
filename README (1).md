# AgriMarketFlow AI

Application web mettant en relation **producteurs**, **collecteurs** et **transporteurs** agricoles à Madagascar. Un producteur publie une récolte disponible, les prestataires proches soumettent des offres, le producteur valide celle qu'il préfère, et une transaction de livraison est créée automatiquement.

## Fonctionnalités

- Inscription / connexion avec trois profils : `Producteur`, `Collecteur`, `Transporteur`
- Publication d'une récolte avec photos et vidéos
- Génération assistée par IA (Groq / Llama) de la description commerciale d'une récolte
- Suggestion automatique des prestataires disponibles à proximité (géolocalisation)
- Soumission d'offres par les prestataires, avec calcul d'un score (prix, distance)
- Validation d'une offre par le producteur : refus automatique des autres offres et ouverture d'une transaction avec suivi de livraison
- API REST en lecture seule pour les récoltes et les suggestions de prestataires

## Stack technique

- **Backend** : Python / Flask
- **Base de données** : SQLite
- **IA générative** : API Groq (modèle `llama-3.1-8b-instant`, gratuite, format compatible OpenAI)
- **Cartographie** : Google Maps API (clé optionnelle)
- **Sécurité** : mots de passe hachés avec `werkzeug.security` (scrypt)

## Structure du projet

```
.
├── app.py            # Application Flask : routes, authentification, logique métier
├── database.py        # Connexion SQLite, schéma des tables, données de démo
├── ia.py               # Intégration de l'API Groq pour générer les descriptions
├── scoring.py          # Calcul de distance et scoring des offres (non fourni ici)
├── static/
│   └── uploads/        # Photos et vidéos des récoltes
├── templates/           # Gabarits HTML (Jinja2)
└── agrimarketflow.db     # Base SQLite (créée automatiquement)
```

## Modèle de données

Cinq tables : `UTILISATEUR`, `RECOLTE`, `RECOLTE_MEDIA`, `OFFRE`, `TRANSACTION`.

Un utilisateur `Producteur` publie une `RECOLTE`, qui peut avoir plusieurs médias associés. Les prestataires (`Collecteur` / `Transporteur`) soumettent des `OFFRE` sur cette récolte. Quand une offre est acceptée, une `TRANSACTION` est créée pour suivre la livraison.

## Installation

```bash
pip install flask werkzeug requests
```

## Configuration (variables d'environnement)

| Variable | Description | Obligatoire |
|---|---|---|
| `GROQ_API_KEY` | Clé API Groq pour la génération de description par IA | Non — la fonctionnalité se désactive proprement si absente |
| `GOOGLE_MAPS_API_KEY` | Clé Google Maps pour l'affichage de la carte | Non |

```bash
export GROQ_API_KEY="votre-cle"
export GOOGLE_MAPS_API_KEY="votre-cle"
```

⚠️ Avant mise en production, remplacez également `app.secret_key` dans `app.py`, actuellement défini en dur (`"dev-secret-key-change-in-production"`).

## Lancement

```bash
python app.py
```

L'application initialise la base (`init_db()`), crée les tables si nécessaire, insère un jeu de données de démonstration si la base est vide, puis démarre le serveur sur `http://localhost:5000` en mode debug.

## Compte de démonstration

Les comptes de test créés au premier lancement partagent tous le mot de passe `password123` :

| Nom | Contact | Profil |
|---|---|---|
| Rakoto Jean | rakoto@mail.mg | Producteur |
| Rasoa Marie | rasoa@mail.mg | Producteur |
| Andria Collect | andria@mail.mg | Collecteur |
| Rabe Négoce | rabe@mail.mg | Collecteur |
| Solo Transport | solo@mail.mg | Transporteur |
| Fara Logistique | fara@mail.mg | Transporteur |

## API REST

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/api/recoltes` | Liste toutes les récoltes |
| `GET` | `/api/recolte/<id>/suggestions` | Prestataires suggérés pour une récolte |
| `POST` | `/api/ia/description` | Génère une description via l'IA (authentifié, Producteur) |

## Flux principal

1. Un producteur crée un compte et publie une récolte (`/recolte/nouvelle`)
2. Les prestataires disponibles à proximité voient la récolte sur leur tableau de bord et soumettent une offre
3. Le producteur consulte les offres reçues, triées par score, sur `/recolte/<id>`
4. Le producteur valide une offre (`/offre/<id>/valider`) : les autres offres sont refusées, la récolte passe en statut *En cours*, une transaction est créée
