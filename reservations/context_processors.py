from reservations.models import Membre, Administrateur
from django.conf import settings


def membre_context(request):
    """Injecte le membre connecté, son statut admin et les clés API dans le contexte"""
    if not request.user.is_authenticated:
        return {}

    try:
        membre = Membre.objects.get(user=request.user)
        is_admin = Administrateur.objects.filter(pk=membre.pk).exists()
        return {
            'membre_global': membre,
            'is_admin': is_admin,
            'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID,
            'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        }
    except Membre.DoesNotExist:
        return {}
