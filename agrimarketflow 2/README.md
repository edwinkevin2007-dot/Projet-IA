# AgriMarketFlow AI — Prototype

Implémentation du Cahier des Charges "AgriMarketFlow AI" (Sujet 7) : mise en relation
producteurs / collecteurs / transporteurs à Madagascar, avec suggestion automatique de
proximité et scoring multicritère (prix, distance, disponibilité).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
python3 app.py
```

L'application démarre sur **http://127.0.0.1:5000**. La base SQLite (`agrimarketflow.db`)
est créée automatiquement au premier lancement, avec des comptes de démonstration :

| Contact             | Rôle         | Mot de passe   |
|----------------------|--------------|----------------|
| rakoto@mail.mg        | Producteur   | password123    |
| andria@mail.mg        | Collecteur   | password123    |
| solo@mail.mg           | Transporteur | password123    |

Pour repartir d'une base vide, supprimez simplement le fichier `agrimarketflow.db`.

## Structure du projet

```
agrimarketflow/
├── app.py            # Routes Flask, authentification, logique métier, uploads
├── database.py        # Schéma SQLite (MLD) + connexion + données de démo
├── scoring.py          # Distance Haversine + moteur de scoring multicritère
├── ia.py                # Intégration API IA gratuite (Groq) : description + agent de mise en relation
├── email_verif.py        # Vérification du domaine email (sans dépendance)
├── requirements.txt
├── templates/           # Vues Jinja2
└── static/
    ├── style.css          # Identité visuelle
    ├── js/maps.js          # Sélecteur de position + carte de matching (Leaflet / OpenStreetMap)
    └── uploads/             # Photos/vidéos des récoltes (créé automatiquement)
```

## Fonctionnalités couvertes (section 3 du cahier des charges)

- **Gestion des profils** : inscription / connexion pour les 3 types d'acteurs.
- **Publication de récoltes** : formulaire produit / quantité / description / localisation,
  avec upload de photos et vidéos du produit.
- **Suggestion automatique (matching local)** : `scoring.prestataires_proches()` calcule
  la distance Haversine entre la récolte et chaque prestataire, et retient ceux dans un
  rayon de 100 km, triés par proximité.
- **Gestion des offres** : les prestataires proposent un prix sur une récolte ; le producteur
  les consulte.
- **Comparaison et scoring** : `scoring.calculer_scores()` normalise prix, distance et
  disponibilité, applique une moyenne pondérée (40 % / 40 % / 20 %, ajustable dans
  `scoring.POIDS`) et classe les offres de la meilleure à la moins bonne.
- **Validation et suivi** : la validation d'une offre par le producteur refuse les autres
  offres, passe la récolte "En cours" et crée une `TRANSACTION`.
- **Interface utilisateur** : interface web (Flask + Jinja2).

## API REST

- `GET /api/recoltes` — liste des récoltes publiées.
- `GET /api/recolte/<id>/suggestions` — prestataires suggérés pour une récolte.

## Modélisation

Le schéma SQLite dans `database.py` reprend fidèlement le MLD du cahier des charges :
`UTILISATEUR`, `RECOLTE`, `OFFRE`, `TRANSACTION`, avec les clés étrangères et contraintes
`CHECK` correspondant aux énumérations (`type_profil`, `statut`, etc.).

## Cartographie — OpenStreetMap (Leaflet)

L'application utilise **Leaflet** avec des tuiles **OpenStreetMap** : entièrement gratuit,
sans clé API, sans compte à créer, sans quota. Utilisé pour :

- **Choisir une position** en cliquant sur la carte ou en glissant le repère, sur les pages
  d'inscription et de publication de récolte (avec un bouton "Me localiser" via la géolocalisation
  du navigateur) ;
- **Visualiser la récolte et les prestataires suggérés** sur une carte, sur la page de détail
  d'une récolte (marqueur rouge = récolte, marqueurs verts/rouges = prestataires disponibles/
  indisponibles, avec distance et score au clic).

Aucune configuration n'est nécessaire — la carte fonctionne dès le lancement de l'application
(connexion internet requise côté navigateur pour charger les tuiles OpenStreetMap, comme pour
n'importe quelle carte web).

La logique des cartes est centralisée dans `static/js/maps.js` (`initPickerMap` pour la sélection
de position, `initRecolteMap` pour la carte de matching).

## Vérification réelle de l'email à l'inscription

À l'inscription, si le contact ressemble à un email, l'application vérifie que **le domaine
existe réellement** (résolution DNS, ex. gmail.com, yahoo.fr...) avant de créer le compte —
sans dépendance externe, sans clé API, gratuit (`email_verif.py`).

**Portée honnête de cette vérification** : elle confirme que le domaine peut recevoir des
emails, mais ne confirme pas qu'une boîte précise existe chez Google/Yahoo/etc. — cela
nécessiterait un handshake SMTP direct que ces fournisseurs bloquent systématiquement pour
lutter contre le spam. C'est le même niveau de vérification gratuite utilisé par la plupart
des frameworks web (Django, Rails...). Si la résolution DNS échoue faute de connexion
sortante sur le serveur, l'inscription n'est pas bloquée à tort : un avertissement s'affiche
et le compte est créé quand même.

## Agent IA de mise en relation entre utilisateurs

La page **Assistant IA** (accessible depuis le menu, pour tout utilisateur connecté) agit comme
un agent qui met les acteurs en relation :

- **Producteur** → l'agent suggère les meilleurs **collecteurs** et **transporteurs** à proximité.
- **Collecteur** → l'agent suggère les meilleurs **producteurs** et **transporteurs** à proximité.
- **Transporteur** → l'agent suggère les meilleurs **producteurs** et **collecteurs** à proximité.

Le classement (`scoring.meilleurs_partenaires()`) est déterministe : disponibilité en priorité,
puis distance (Haversine). Un bouton **"Demander l'avis de l'agent IA"** appelle ensuite l'API
gratuite Groq pour rédiger, en langage naturel, une courte recommandation expliquant avec qui
entrer en contact en priorité et pourquoi (`ia.generer_avis_partenaires()`). Chaque partenaire
suggéré est directement contactable (email ou téléphone) en un clic.

## Médias et description produit

Chaque récolte peut désormais inclure :
- une **description** libre (qualité, fraîcheur, conditions de récolte...) ;
- des **photos** (JPG, PNG, GIF, WEBP) et des **vidéos** (MP4, WEBM, MOV), plusieurs fichiers
  possibles, affichés en galerie sur la page de détail et en vignette sur les tableaux de bord.

Les fichiers sont stockés dans `static/uploads/recoltes/<id_recolte>/` et référencés dans la
table `RECOLTE_MEDIA`. Taille maximale par requête : 50 Mo (`MAX_CONTENT_LENGTH`, ajustable
dans `app.py`).

## Assistant IA (gratuit) pour la description produit

Un bouton **"✨ Générer avec l'IA"** sur le formulaire de publication rédige automatiquement
une description commerciale à partir du nom du produit et de la quantité, via l'API gratuite
de [Groq](https://console.groq.com) (modèles Llama, inférence très rapide, aucune carte
bancaire requise).

### Configuration de la clé Groq

1. Créez un compte gratuit sur [console.groq.com](https://console.groq.com) et générez une clé API.
2. Définissez-la en variable d'environnement :

```bash
export GROQ_API_KEY="votre-cle-groq"
python3 app.py
```

Sans clé configurée, le bouton est simplement désactivé et un message informe l'utilisateur
que la description doit être rédigée manuellement — le reste de l'application n'est pas affecté.

La logique d'appel est isolée dans `ia.py` (`generer_description()`), volontairement découplée
du reste du code pour pouvoir être remplacée par un autre fournisseur gratuit
(Hugging Face Inference API, Google Gemini free tier, etc.) sans toucher aux routes Flask.

## Limites du prototype

- Authentification simple par session Flask (à durcir pour une mise en production : CSRF,
  HTTPS, limitation de tentatives, etc.).
- La vérification email confirme l'existence du domaine, pas d'une boîte mail précise
  (voir explication détaillée plus haut).
- L'agent IA (Groq) est optionnel : sans clé, l'application reste pleinement fonctionnelle,
  seule la rédaction en langage naturel n'est pas disponible (le classement déterministe l'est
  toujours).
