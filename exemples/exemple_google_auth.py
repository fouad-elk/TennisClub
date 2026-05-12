"""
============================================================
EXEMPLE : Authentification Google Identity Services
============================================================
Ce script montre comment vérifier un token Google (JWT)
côté serveur avec Python, sans framework.

Prérequis :
    pip install google-auth requests

Fonctionnement :
    1. L'utilisateur clique sur le bouton "Se connecter avec Google"
       dans le navigateur (côté client, via le SDK JavaScript de Google).
    2. Google renvoie un token JWT (JSON Web Token) signé.
    3. Ce token est envoyé au serveur (ici, ce script).
    4. Le serveur vérifie le token avec la librairie google-auth.
    5. Si le token est valide, on récupère les infos de l'utilisateur
       (email, nom, photo de profil).

Documentation officielle :
    https://developers.google.com/identity/gsi/web/guides/overview
============================================================
"""

from google.oauth2 import id_token
from google.auth.transport import requests

# L'identifiant client Google (à récupérer sur https://console.cloud.google.com)
GOOGLE_CLIENT_ID = "VOTRE_CLIENT_ID.apps.googleusercontent.com"


def verifier_token_google(token_jwt):
    """
    Vérifie un token JWT Google et renvoie les informations de l'utilisateur.

    Paramètres :
        token_jwt (str) : Le token JWT reçu du navigateur après connexion Google.

    Retour :
        dict : Les informations de l'utilisateur (email, nom, photo).
        None : Si le token est invalide.
    """
    try:
        # Vérification du token avec la librairie Google
        # Cette fonction vérifie :
        #   - La signature du token (authenticité)
        #   - La date d'expiration
        #   - L'audience (notre CLIENT_ID)
        infos = id_token.verify_oauth2_token(
            token_jwt,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        # Si on arrive ici, le token est valide
        # On extrait les informations utiles
        email = infos.get('email')
        nom = infos.get('name')
        photo = infos.get('picture')

        print(f"Connexion réussie !")
        print(f"  Email : {email}")
        print(f"  Nom   : {nom}")
        print(f"  Photo : {photo}")

        return {
            'email': email,
            'nom': nom,
            'photo': photo,
        }

    except ValueError as erreur:
        # Le token est invalide (expiré, mauvaise signature, etc.)
        print(f"Token invalide : {erreur}")
        return None


# --- Point d'entrée ---
if __name__ == '__main__':
    print("=== Exemple Google Identity Services ===")
    print()
    print("Ce script vérifie un token JWT Google côté serveur.")
    print("En production, le token est envoyé par le navigateur après")
    print("que l'utilisateur ait cliqué sur 'Se connecter avec Google'.")
    print()

    # En situation réelle, le token viendrait du frontend (JavaScript)
    # Ici on montre la structure du code de vérification
    token_exemple = "COLLER_ICI_LE_TOKEN_JWT_DU_NAVIGATEUR"

    if token_exemple == "COLLER_ICI_LE_TOKEN_JWT_DU_NAVIGATEUR":
        print("Pour tester : remplacez la variable 'token_exemple'")
        print("par un vrai token JWT obtenu depuis le bouton Google.")
        print()
        print("--- Côté HTML (navigateur) ---")
        print("""
<script src="https://accounts.google.com/gsi/client" async defer></script>

<div id="g_id_onload"
     data-client_id="VOTRE_CLIENT_ID.apps.googleusercontent.com"
     data-callback="onSignIn">
</div>
<div class="g_id_signin" data-type="standard"></div>

<script>
function onSignIn(response) {
    // response.credential contient le token JWT
    // On l'envoie au serveur Python via fetch
    fetch('/verifier-google/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token: response.credential})
    })
    .then(resp => resp.json())
    .then(data => console.log('Utilisateur:', data));
}
</script>
        """)
    else:
        resultat = verifier_token_google(token_exemple)
        if resultat:
            print(f"\nUtilisateur vérifié : {resultat['email']}")
        else:
            print("\nÉchec de la vérification.")
