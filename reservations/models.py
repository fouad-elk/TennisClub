from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from datetime import date

# Validateur pour le numéro AFT : 7 chiffres, commence pas par 0
numero_aft_validator = RegexValidator(
    regex=r'^[1-9]\d{6}$',
    message="Le numéro d'affiliation doit faire 7 chiffres et ne pas commencer par 0."
)

class Categorie(models.Model):
    nom = models.CharField(max_length=50)
    age_min = models.IntegerField()
    age_max = models.IntegerField()
    # Année de naissance min/max (pour la saison en cours)
    annee_naissance_min = models.IntegerField(null=True, blank=True)
    annee_naissance_max = models.IntegerField(null=True, blank=True)
    sexe = models.CharField(max_length=1, choices=[('M', 'M'), ('F', 'F')])
    # Une catégorie peut en inclure une autre (ex: Dames inclut Dames 25)
    categorie_inclus = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nom

    def get_liste_membres(self):
        """Renvoie tous les membres qui correspondent à cette catégorie"""
        today = date.today()
        return Membre.objects.filter(
            sexe=self.sexe,
            date_naissance__year__lte=today.year - self.age_min,
            date_naissance__year__gte=today.year - self.age_max,
        )

class Membre(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    numero_affiliation = models.CharField(
        max_length=7, unique=True, validators=[numero_aft_validator]
    )
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    rue = models.CharField(max_length=255)
    code_postal = models.CharField(max_length=10)
    localite = models.CharField(max_length=100)
    gsm = models.CharField(max_length=20)
    email = models.EmailField(unique=True)

    # Tous les classements AFT possibles
    CLASSEMENTS = [
        ('A', 'A'),
        ('B-15.4', 'B-15.4'), ('B-15.2', 'B-15.2'), ('B-15.1', 'B-15.1'),
        ('B15', 'B15'),
        ('B-4/6', 'B-4/6'), ('B-2/6', 'B-2/6'),
        ('B0', 'B0'),
        ('B+2/6', 'B+2/6'), ('B+4/6', 'B+4/6'),
        ('C15', 'C15'), ('C15.1', 'C15.1'), ('C15.2', 'C15.2'),
        ('C15.3', 'C15.3'), ('C15.4', 'C15.4'),
        ('C30', 'C30'), ('C30.1', 'C30.1'), ('C30.2', 'C30.2'),
        ('C30.3', 'C30.3'), ('C30.4', 'C30.4'), ('C30.5', 'C30.5'),
        ('N.C', 'N.C'),
    ]
    classement = models.CharField(max_length=10, choices=CLASSEMENTS, default='N.C')
    sexe = models.CharField(max_length=1, choices=[('M', 'M'), ('F', 'F')])
    date_naissance = models.DateField()
    en_ordre_cotisation = models.BooleanField(default=False)

    # Champs pour le paiement Stripe et l'auth Google
    google_email = models.EmailField(null=True, blank=True)
    date_echeance = models.DateField(null=True, blank=True)
    date_dernier_paiement = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def get_age(self):
        """Calcule l'âge du membre"""
        today = date.today()
        return today.year - self.date_naissance.year - (
            (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    def get_categories(self):
        """Renvoie les catégories du membre selon son âge et son sexe"""
        age = self.get_age()
        return Categorie.objects.filter(
            age_min__lte=age, age_max__gte=age, sexe=self.sexe
        )

class Administrateur(Membre):
    class Meta:
        verbose_name = "Administrateur"

class Terrain(models.Model):
    numero = models.IntegerField(unique=True)
    surface = models.CharField(max_length=50, default='Terre Battue')

    def __str__(self):
        return f"Court {self.numero}"

class ActionTerrain(models.Model):
    terrain = models.ForeignKey(Terrain, on_delete=models.CASCADE)
    date = models.DateField()
    heure_debut = models.IntegerField()
    duree = models.IntegerField(default=1)
    # Statut du créneau (comme sur le diagramme)
    STATUTS = [('libre', 'Libre'), ('reserve', 'Réservé'), ('bloque', 'Bloqué')]
    statut = models.CharField(max_length=10, choices=STATUTS, default='libre')

    class Meta:
        abstract = True

class Reserver(ActionTerrain):
    membres = models.ManyToManyField(Membre)

class Bloquer(ActionTerrain):
    administrateur = models.ForeignKey(Administrateur, on_delete=models.CASCADE)
    raison = models.CharField(max_length=200)