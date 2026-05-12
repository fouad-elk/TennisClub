from django import forms
from .models import Reserver, Membre, Terrain, Bloquer, Administrateur, Categorie
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models import F
from datetime import timedelta, date, datetime

# --- Formulaire mot de passe oublié — étape 1 : vérification identité ---
class MotDePasseOublieForm(forms.Form):
    numero_affiliation = forms.CharField(
        max_length=7, min_length=7,
        label="Numéro d'affiliation"
    )
    date_naissance = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date de naissance",
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
    )

    def clean(self):
        cd = super().clean()
        num = cd.get('numero_affiliation')
        dob = cd.get('date_naissance')
        if num and dob:
            try:
                membre = Membre.objects.get(numero_affiliation=num)
            except Membre.DoesNotExist:
                raise ValidationError("Numéro d'affiliation introuvable.")
            if membre.date_naissance != dob:
                raise ValidationError("La date de naissance ne correspond pas à ce numéro.")
            if membre.user is None:
                raise ValidationError("Aucun compte créé pour ce numéro. Utilise 'Première connexion'.")
        return cd


# --- Formulaire mot de passe oublié — étape 2 : nouveau mot de passe ---
class NouveauMotDePasseForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Nouveau mot de passe",
        min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmer le mot de passe",
        min_length=8
    )

    def clean(self):
        cd = super().clean()
        p1 = cd.get('password1')
        p2 = cd.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les deux mots de passe ne correspondent pas.")
        return cd


# --- Formulaire de connexion par numéro d'affiliation ---
class LoginAffiliationForm(forms.Form):
    numero_affiliation = forms.CharField(
        max_length=7, min_length=7,
        label="Numéro d'affiliation"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Mot de passe"
    )

# --- Formulaire première connexion (créer son mot de passe) ---
class PremiereConnexionForm(forms.Form):
    numero_affiliation = forms.CharField(
        max_length=7, min_length=7,
        label="Numéro d'affiliation"
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Mot de passe",
        min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmer le mot de passe",
        min_length=8
    )

    def clean(self):
        cd = super().clean()
        # Vérifier que le numéro d'affiliation existe
        num = cd.get('numero_affiliation')
        if num and not Membre.objects.filter(numero_affiliation=num).exists():
            raise ValidationError("Ce numéro d'affiliation n'existe pas dans le club.")

        # Vérifier que le membre n'a pas déjà un compte
        if num:
            membre = Membre.objects.filter(numero_affiliation=num).first()
            if membre and membre.user is not None:
                raise ValidationError("Tu as déjà un compte. Utilise la page de connexion.")

        # Vérifier que les deux mots de passe sont identiques
        p1 = cd.get('password1')
        p2 = cd.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les deux mots de passe ne correspondent pas.")
        return cd

# --- Formulaire de réservation avec les règles métier ---
class ReserverForm(forms.ModelForm):
    # Le type de match pour savoir si c'est simple ou double
    TYPE_CHOICES = [('simple', 'Simple (1h)'), ('double', 'Double (2h)')]
    type_match = forms.ChoiceField(choices=TYPE_CHOICES, label="Type de match")

    def __init__(self, *args, membre_connecte=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membre_connecte = membre_connecte
        # Seuls les membres en ordre de cotisation apparaissent (sans le membre connecté)
        qs = Membre.objects.filter(en_ordre_cotisation=True)
        if membre_connecte:
            qs = qs.exclude(pk=membre_connecte.pk)
        self.fields['membres'].queryset = qs
        self.fields['membres'].label = "Partenaire(s)"

    class Meta:
        model = Reserver
        fields = ['terrain', 'date', 'heure_debut', 'membres']
        widgets = {
            'terrain': forms.HiddenInput(),
            'date': forms.HiddenInput(),
            'heure_debut': forms.HiddenInput(),
            'membres': forms.SelectMultiple(attrs={'class': 'form-input'})
        }

    def clean(self):
        cd = super().clean()
        terrain = cd.get('terrain')
        date_resa = cd.get('date')
        heure = cd.get('heure_debut')
        type_match = cd.get('type_match')
        membres = cd.get('membres')

        if not all([terrain, date_resa, heure is not None, type_match, membres]):
            return cd

        # Durée selon le type
        duree = 1 if type_match == 'simple' else 2
        nb_joueurs = membres.count()

        # --- Pas de réservation dans le passé ---
        maintenant = datetime.now()
        resa_dt = datetime.combine(date_resa, datetime.min.time().replace(hour=heure))
        if resa_dt <= maintenant:
            raise ValidationError("Tu ne peux pas réserver un créneau dans le passé.")

        # --- L'heure doit être entre 9h et 21h (pour finir au plus tard à 22h) ---
        if heure < 9 or heure >= 22:
            raise ValidationError("L'heure doit être entre 9h et 21h.")

        # --- Le créneau ne doit pas dépasser 22h ---
        if heure + duree > 22:
            raise ValidationError("La réservation dépasse les horaires (fin max 22h).")

        # Simple = 1 partenaire, Double = 3 partenaires (le membre connecté est ajouté automatiquement)
        if type_match == 'simple' and nb_joueurs != 1:
            raise ValidationError("En simple, choisis 1 partenaire.")
        if type_match == 'double' and nb_joueurs != 3:
            raise ValidationError("En double, choisis 3 partenaires.")

        # --- Le membre connecté doit être en ordre de cotisation ---
        if self.membre_connecte and not self.membre_connecte.en_ordre_cotisation:
            raise ValidationError("Tu n'es pas en ordre de cotisation.")

        # --- Tous les partenaires doivent être en ordre de cotisation ---
        for m in membres:
            if not m.en_ordre_cotisation:
                raise ValidationError(f"{m} n'est pas en ordre de cotisation.")

        # --- Vérifier que le terrain est libre (gère les chevauchements 2h) ---
        conflit_terrain = Reserver.objects.filter(
            terrain=terrain,
            date=date_resa,
            heure_debut__lt=heure + duree,           # existant commence avant notre fin
            heure_debut__gt=heure - F('duree'),       # existant finit après notre début
        )
        if conflit_terrain.exists():
            raise ValidationError("Ce terrain est déjà réservé sur ce créneau.")

        # --- Vérifier que le terrain n'est pas bloqué  ---
        conflit_blocage = Bloquer.objects.filter(
            terrain=terrain,
            date=date_resa,
            heure_debut__lt=heure + duree,
            heure_debut__gt=heure - F('duree'),
        )
        if conflit_blocage.exists():
            raise ValidationError("Ce terrain est bloqué sur ce créneau.")

        # --- Vérifier qu'aucun joueur n'est sur un autre terrain au même moment ---
        tous_joueurs = list(membres)
        if self.membre_connecte:
            tous_joueurs.append(self.membre_connecte)
        for m in tous_joueurs:
            conflit_membre = Reserver.objects.filter(
                membres=m,
                date=date_resa,
                heure_debut__lt=heure + duree,
                heure_debut__gt=heure - F('duree'),
            )
            if conflit_membre.exists():
                raise ValidationError(
                    f"{m} a déjà une réservation qui chevauche ce créneau."
                )

        # --- Quotas hebdomadaires pour TOUS les joueurs ---
        for m in tous_joueurs:
            self._verifier_quota(m, date_resa, duree)

        # Stocker la durée calculée pour la vue
        cd['duree_calculee'] = duree
        return cd

    def _verifier_quota(self, membre, date_resa, duree_demandee):
        """Vérifie le quota hebdo du membre (dimanche → samedi)"""
        # Trouver le dimanche de début de semaine
        jour = date_resa.weekday()  # 0=lundi ... 6=dimanche
        if jour == 6:
            debut = date_resa
        else:
            debut = date_resa - timedelta(days=jour + 1)
        fin = debut + timedelta(days=6)

        # Compter les heures déjà réservées cette semaine
        resas = Reserver.objects.filter(
            membres=membre, date__gte=debut, date__lte=fin
        )
        h_simple = 0
        h_double = 0
        for r in resas:
            if r.duree == 1:
                h_simple += 1
            else:
                h_double += r.duree

        # Ajouter la demande en cours
        if duree_demandee == 1:
            h_simple += 1
        else:
            h_double += duree_demandee

        # Règle : max 2h simple seul
        if h_double == 0 and h_simple > 2:
            raise ValidationError("Max 2h de simple par semaine.")
        # Règle : max 4h double seul
        if h_simple == 0 and h_double > 4:
            raise ValidationError("Max 4h de double par semaine.")
        # Règle : mix = max 1h simple + 2h double
        if h_simple > 0 and h_double > 0:
            if h_simple > 1:
                raise ValidationError("En combiné, max 1h de simple par semaine.")
            if h_double > 2:
                raise ValidationError("En combiné, max 2h de double par semaine.")


# --- Formulaire pour ajouter/modifier un membre (admin) ---
class MembreForm(forms.ModelForm):
    class Meta:
        model = Membre
        fields = ['numero_affiliation', 'nom', 'prenom', 'rue', 'code_postal',
                  'localite', 'gsm', 'email', 'classement', 'sexe', 'date_naissance']
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
        }


# --- Formulaire pour ajouter un terrain (admin) ---
class TerrainForm(forms.ModelForm):
    class Meta:
        model = Terrain
        fields = ['numero', 'surface']

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        # Vérifier que le numéro n'existe pas déjà
        if Terrain.objects.filter(numero=numero).exists():
            raise ValidationError("Un terrain avec ce numéro existe déjà.")
        return numero


# --- Formulaire pour bloquer un terrain (admin) ---
class BloquerForm(forms.ModelForm):
    class Meta:
        model = Bloquer
        fields = ['terrain', 'date', 'heure_debut', 'duree', 'raison']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cd = super().clean()
        terrain = cd.get('terrain')
        date_blocage = cd.get('date')
        heure = cd.get('heure_debut')
        duree = cd.get('duree', 1)

        if not all([terrain, date_blocage, heure is not None]):
            return cd

        # L'heure doit être entre 9h et 22h
        if heure < 9 or heure > 22:
            raise ValidationError("L'heure doit être entre 9h et 22h.")

        # Le blocage ne doit pas dépasser 22h
        if heure + duree > 23:
            raise ValidationError("Le blocage dépasse les horaires (max 22h).")

        return cd


# --- Formulaire pour modifier son profil (membre) ---
class ProfilForm(forms.ModelForm):
    class Meta:
        model = Membre
        fields = ['rue', 'code_postal', 'localite', 'gsm', 'email']


# --- Formulaire pour changer son mot de passe ---
class ChangerMotDePasseForm(forms.Form):
    ancien = forms.CharField(widget=forms.PasswordInput, label="Ancien mot de passe")
    nouveau1 = forms.CharField(widget=forms.PasswordInput, label="Nouveau mot de passe", min_length=8)
    nouveau2 = forms.CharField(widget=forms.PasswordInput, label="Confirmer", min_length=8)

    def clean(self):
        cd = super().clean()
        p1 = cd.get('nouveau1')
        p2 = cd.get('nouveau2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Les deux mots de passe ne correspondent pas.")
        return cd