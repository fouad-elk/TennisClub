from django.contrib import admin
from .models import Categorie, Membre, Administrateur, Terrain, Reserver, Bloquer


# === Admin personnalisé pour le modèle Membre ===
# Permet de filtrer, chercher et modifier les membres depuis l'interface Django admin
@admin.register(Membre)
class MembreAdmin(admin.ModelAdmin):
    # Colonnes visibles dans la liste
    list_display = [
        'numero_affiliation', 'nom', 'prenom',
        'en_ordre_cotisation', 'date_echeance', 'date_dernier_paiement',
    ]
    # Filtres rapides dans la barre latérale
    list_filter = ['en_ordre_cotisation']
    # Champs dans lesquels on peut chercher
    search_fields = ['nom', 'prenom', 'numero_affiliation']
    # Actions groupées pour activer/désactiver plusieurs membres d'un coup
    actions = ['activer_cotisation', 'desactiver_cotisation']

    @admin.action(description="Activer la cotisation des membres sélectionnés")
    def activer_cotisation(self, request, queryset):
        nb = queryset.update(en_ordre_cotisation=True)
        self.message_user(request, f"{nb} membre(s) activé(s).")

    @admin.action(description="Désactiver la cotisation des membres sélectionnés")
    def desactiver_cotisation(self, request, queryset):
        nb = queryset.update(en_ordre_cotisation=False)
        self.message_user(request, f"{nb} membre(s) désactivé(s).")


# Enregistrement des autres modèles
admin.site.register(Categorie)
admin.site.register(Administrateur)
admin.site.register(Terrain)
admin.site.register(Reserver)
admin.site.register(Bloquer)