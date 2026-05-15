# Tennis Club — Application de réservation de courts

Projet d'intégration — Bachelier en Informatique de Gestion  
Année académique 2025-2026

---

## Description

Application web de gestion d'un club de tennis développée avec **Django 6** et **PostgreSQL**.  
Elle permet aux membres de réserver des courts en ligne, de renouveler leur cotisation via paiement sécurisé (Stripe), et offre un espace d'administration pour gérer les membres et les terrains.

---

## Fonctionnalités

### Membres
- Connexion par numéro d'affiliation
- Première connexion avec création de mot de passe
- Réservation de courts (simple ou double) avec vérification en temps réel
- Annulation de réservation (règle des 24h respectée)
- Annuaire des membres avec recherche et filtres
- Profil personnel (modification coordonnées, changement de mot de passe)
- Renouvellement de cotisation via **Google Identity Services** + **Stripe**

### Administrateurs
- Activation / désactivation des cotisations membres
- Ajout, modification, suppression de membres
- Ajout, suppression de terrains (avec gestion des réservations en conflit)
- Blocage de terrains (entretien, événements)

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3 · Django 6.0 |
| Base de données | PostgreSQL 16 |
| Paiement | Stripe Checkout (mode test) |
| Authentification Google | Google Identity Services (OAuth 2.0 / JWT) |
| Frontend | HTML5 · CSS3 · JavaScript vanilla · SweetAlert2 |
| Serveur WSGI | Gunicorn (développement : `runserver`) |

---

## Installation

### Prérequis
- Python 3.12+
- PostgreSQL 16
- Un compte Stripe (mode test)

### 1. Cloner le dépôt
```bash
git clone https://github.com/fouad-elk/TennisClub.git
cd TennisClub
```

### 2. Créer et activer l'environnement virtuel
```bash
python -m venv env
# Windows
.\env\Scripts\Activate.ps1
# Linux / Mac
source env/bin/activate
```

### 3. Installer les dépendances
```bash
pip install django psycopg2-binary stripe requests
```

### 4. Configurer la base de données PostgreSQL
Créer une base `TennisDB` et un utilisateur, puis mettre à jour `config/settings.py` :
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'TennisDB',
        'USER': 'votre_user',
        'PASSWORD': 'votre_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 5. Configurer les clés API dans `config/settings.py`
```python
STRIPE_PUBLIC_KEY = 'pk_test_...'
STRIPE_SECRET_KEY = 'sk_test_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'
GOOGLE_CLIENT_ID = '...'
```

### 6. Appliquer les migrations et lancer le serveur
```bash
python manage.py migrate
python manage.py runserver
```

L'application est accessible à l'adresse : http://127.0.0.1:8000

---

## Structure du projet

```
TennisClub/
├── config/                  # Configuration Django (settings, urls, wsgi)
├── reservations/            # Application principale
│   ├── models.py            # Modèles : Membre, Terrain, Reserver, Bloquer...
│   ├── views.py             # Toutes les vues + API AJAX + Stripe + Google Auth
│   ├── forms.py             # Formulaires Django
│   ├── templates/           # Templates HTML
│   └── static/              # CSS, JS, images
└── manage.py
```

---

## Flux de paiement de la cotisation

```
Membre non en ordre → Modale automatique
    → Connexion Google (JWT décodé côté JS)
    → Email envoyé au serveur via AJAX (/google-auth/)
    → Bouton Stripe révélé
    → Redirection vers Stripe Checkout (/paiement/)
    → Confirmation via webhook (/webhook/stripe/) + page retour
    → Cotisation activée en base de données
```

---

## Auteurs

- **Fouad EL KOURATI**  
  Bachelier en Informatique de Gestion — Haute École  
  Année 2025-2026
