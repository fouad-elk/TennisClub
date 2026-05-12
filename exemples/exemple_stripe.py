"""
============================================================
EXEMPLE : Paiement en ligne avec Stripe Checkout
============================================================
Ce script montre comment créer une session de paiement Stripe
côté serveur avec Python, sans framework.

Prérequis :
    pip install stripe

Fonctionnement :
    1. Le client (navigateur) clique sur "Payer".
    2. Le serveur crée une "session de paiement" via l'API Stripe.
    3. Stripe renvoie une URL de paiement sécurisée.
    4. Le client est redirigé vers cette URL (hébergée par Stripe).
    5. Après paiement, Stripe redirige vers notre site (succès ou annulation).
    6. Stripe envoie aussi un "webhook" (notification serveur) pour confirmer.

Documentation officielle :
    https://docs.stripe.com/checkout/quickstart
============================================================
"""

import stripe

# Clés API Stripe (à récupérer sur https://dashboard.stripe.com/apikeys)
# ATTENTION : ne jamais partager la clé secrète !
# En mode test, les clés commencent par "sk_test_" et "pk_test_"
stripe.api_key = "sk_test_VOTRE_CLE_SECRETE_ICI"
CLE_PUBLIQUE = "pk_test_VOTRE_CLE_PUBLIQUE_ICI"


def creer_session_paiement(montant_euros, description, email_client):
    """
    Crée une session de paiement Stripe Checkout.

    Paramètres :
        montant_euros (int) : Montant à payer en euros (ex: 50 pour 50€).
        description (str)   : Description du produit/service.
        email_client (str)  : Email du client (pré-rempli dans le formulaire).

    Retour :
        str : L'URL de la page de paiement Stripe.
        None : En cas d'erreur.
    """
    try:
        # Stripe utilise les centimes (50€ = 5000 centimes)
        montant_centimes = montant_euros * 100

        # Création de la session de paiement
        session = stripe.checkout.Session.create(
            # Mode "payment" = paiement unique (pas un abonnement)
            mode='payment',

            # Ce qu'on vend (liste d'articles)
            line_items=[{
                'price_data': {
                    'currency': 'eur',                # Devise : euros
                    'unit_amount': montant_centimes,   # Prix en centimes
                    'product_data': {
                        'name': description,           # Nom affiché sur la page
                    },
                },
                'quantity': 1,                         # Quantité
            }],

            # Email pré-rempli dans le formulaire Stripe
            customer_email=email_client,

            # Où rediriger après le paiement
            success_url='http://localhost:8000/succes/',   # Paiement réussi
            cancel_url='http://localhost:8000/annule/',     # Paiement annulé
        )

        print(f"Session créée avec succès !")
        print(f"  ID session : {session.id}")
        print(f"  URL paiement : {session.url}")

        return session.url

    except stripe.error.StripeError as erreur:
        print(f"Erreur Stripe : {erreur}")
        return None


def traiter_webhook(payload, signature, webhook_secret):
    """
    Traite un webhook Stripe (notification de paiement).

    Quand un paiement est effectué, Stripe envoie une requête POST
    à notre serveur avec les détails du paiement. Cette fonction
    vérifie et traite cette notification.

    Paramètres :
        payload (bytes)       : Le corps de la requête HTTP.
        signature (str)       : L'en-tête 'Stripe-Signature'.
        webhook_secret (str)  : Le secret du webhook (dashboard Stripe).

    Retour :
        dict : Les détails du paiement si valide.
        None : Si la signature est invalide.
    """
    try:
        # Vérification de la signature (sécurité)
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )

        # On ne traite que les paiements réussis
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            email = session.get('customer_email')
            montant = session.get('amount_total', 0) / 100  # Centimes → euros

            print(f"Paiement reçu !")
            print(f"  Email : {email}")
            print(f"  Montant : {montant}€")

            return {
                'email': email,
                'montant': montant,
                'session_id': session['id'],
            }
        else:
            print(f"Événement ignoré : {event['type']}")
            return None

    except stripe.error.SignatureVerificationError:
        print("Signature invalide ! Requête rejetée.")
        return None


# --- Point d'entrée ---
if __name__ == '__main__':
    print("=== Exemple Stripe Checkout ===")
    print()

    # Vérifier que les clés sont configurées
    if "VOTRE_CLE" in stripe.api_key:
        print("ATTENTION : Remplacez les clés API par vos vraies clés Stripe.")
        print("Récupérez-les sur : https://dashboard.stripe.com/apikeys")
        print()
        print("--- Comment ça marche ---")
        print()
        print("1. Créer un compte Stripe (gratuit)")
        print("2. Récupérer les clés de test (sk_test_... et pk_test_...)")
        print("3. Remplacer les clés dans ce script")
        print("4. Lancer le script : python exemple_stripe.py")
        print("5. Ouvrir l'URL affichée dans le navigateur")
        print("6. Utiliser la carte de test : 4242 4242 4242 4242")
        print("   Date : n'importe quelle date future, CVC : 123")
        print()
        print("--- Code côté HTML (navigateur) ---")
        print("""
<!-- Bouton de paiement -->
<a href="/paiement/" class="btn">Payer 50€</a>

<!-- Côté serveur (Django), la vue redirige vers Stripe -->
<!-- Après paiement, Stripe redirige vers /succes/ ou /annule/ -->
        """)
    else:
        # Créer une vraie session de paiement (mode test)
        url = creer_session_paiement(
            montant_euros=50,
            description="Cotisation Tennis Club — Saison 2025",
            email_client="membre@example.com"
        )

        if url:
            print(f"\nOuvrez cette URL dans votre navigateur pour tester :")
            print(f"  {url}")
            print(f"\nCarte de test : 4242 4242 4242 4242")
