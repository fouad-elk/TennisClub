from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from reservations.views import (
    home, login_view, premiere_connexion, creer_reservation, supprimer_reservation,
    annuaire, mes_reservations, mon_profil,
    admin_activation_membres, admin_ajout_membre, admin_modifier_membre,
    admin_supprimer_membre, admin_liste_membres,
    admin_ajout_terrain, admin_supprimer_terrain, admin_liste_terrains,
    admin_bloquer_terrain, admin_supprimer_reservation,
    google_auth, creer_session_paiement, stripe_webhook,
    paiement_succes, paiement_annule, api_recherche_annuaire,
    dashboard, mdp_oublie, mdp_nouveau, api_disponibilite,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('premiere-connexion/', premiere_connexion, name='premiere_connexion'),
    path('mot-de-passe-oublie/', mdp_oublie, name='mdp_oublie'),
    path('mot-de-passe-oublie/nouveau/', mdp_nouveau, name='mdp_nouveau'),

    # Réservations
    path('reserver/', creer_reservation, name='creer_reservation'),
    path('supprimer-reservation/<int:pk>/', supprimer_reservation, name='supprimer_reservation'),

    # Pages membres
    path('annuaire/', annuaire, name='annuaire'),
    path('mes-reservations/', mes_reservations, name='mes_reservations'),
    path('profil/', mon_profil, name='mon_profil'),

    # Paiement : Google Auth + Stripe
    path('google-auth/', google_auth, name='google_auth'),
    path('paiement/', creer_session_paiement, name='creer_session_paiement'),
    path('paiement/succes/', paiement_succes, name='paiement_succes'),
    path('paiement/annule/', paiement_annule, name='paiement_annule'),
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),

    # API AJAX (programmation asynchrone)
    path('api/annuaire/', api_recherche_annuaire, name='api_recherche_annuaire'),
    path('api/disponibilite/', api_disponibilite, name='api_disponibilite'),

    # Admin : gestion membres
    path('gestion/membres/', admin_liste_membres, name='admin_liste_membres'),
    path('gestion/membres/activation/', admin_activation_membres, name='admin_activation_membres'),
    path('gestion/membres/ajouter/', admin_ajout_membre, name='admin_ajout_membre'),
    path('gestion/membres/modifier/<int:pk>/', admin_modifier_membre, name='admin_modifier_membre'),
    path('gestion/membres/supprimer/<int:pk>/', admin_supprimer_membre, name='admin_supprimer_membre'),

    # Admin : gestion terrains
    path('gestion/terrains/', admin_liste_terrains, name='admin_liste_terrains'),
    path('gestion/terrains/ajouter/', admin_ajout_terrain, name='admin_ajout_terrain'),
    path('gestion/terrains/supprimer/<int:pk>/', admin_supprimer_terrain, name='admin_supprimer_terrain'),

    # Admin : blocage + suppression résa
    path('gestion/bloquer/', admin_bloquer_terrain, name='admin_bloquer_terrain'),
    path('gestion/supprimer-reservation/<int:pk>/', admin_supprimer_reservation, name='admin_supprimer_reservation'),
]

# Servir les fichiers statiques en mode développement
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
