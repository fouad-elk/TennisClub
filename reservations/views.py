from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Terrain, Membre, Reserver, Bloquer, Administrateur, Categorie
from .forms import (ReserverForm, LoginAffiliationForm, PremiereConnexionForm,
                    MembreForm, TerrainForm, BloquerForm, ProfilForm, ChangerMotDePasseForm,
                    MotDePasseOublieForm, NouveauMotDePasseForm)
from datetime import date, timedelta, datetime
from django.utils import timezone
import stripe
import json

# Configuration de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ============================================================
#  DECORATEUR : cotisation_requise
#  Bloque l'accès aux vues protégées si le membre n'est pas en ordre
# ============================================================
def cotisation_requise(view_func):
    """Vérifie que le membre est en ordre de cotisation avant d'accéder à la vue"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            membre = Membre.objects.get(user=request.user)
            if not membre.en_ordre_cotisation:
                messages.error(request, "Tu dois être en ordre de cotisation pour accéder à cette fonctionnalité.")
                return redirect('home')
        except Membre.DoesNotExist:
            messages.error(request, "Profil introuvable.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


# --- Connexion par numéro d'affiliation ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginAffiliationForm()
    if request.method == 'POST':
        form = LoginAffiliationForm(request.POST)
        if form.is_valid():
            num = form.cleaned_data['numero_affiliation']
            password = form.cleaned_data['password']

            # Chercher le membre avec ce numéro
            try:
                membre = Membre.objects.get(numero_affiliation=num)
            except Membre.DoesNotExist:
                messages.error(request, "Numéro d'affiliation inconnu.")
                return render(request, 'reservations/login.html', {'form': form})

            # Vérifier que le membre a bien un compte User
            if membre.user is None:
                messages.error(request, "Première connexion ? Crée d'abord ton mot de passe.")
                return redirect('premiere_connexion')
            # Tenter la connexion avec le username du User lié
            user = authenticate(request, username=membre.user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Mot de passe incorrect.")

    return render(request, 'reservations/login.html', {'form': form})


# --- Première connexion : créer son mot de passe ---
def premiere_connexion(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = PremiereConnexionForm()
    if request.method == 'POST':
        form = PremiereConnexionForm(request.POST)
        if form.is_valid():
            num = form.cleaned_data['numero_affiliation']
            password = form.cleaned_data['password1']

            membre = Membre.objects.get(numero_affiliation=num)

            # Créer un User Django lié au membre
            user = User.objects.create_user(
                username=num,  # le username = numéro d'affiliation
                password=password,
                email=membre.email,
                first_name=membre.prenom,
                last_name=membre.nom,
            )
            membre.user = user
            membre.save()

            # Connecter directement le membre
            login(request, user)
            messages.success(request, "Compte créé ! Bienvenue au club.")
            return redirect('dashboard')

    return render(request, 'reservations/premiere_connexion.html', {'form': form})


# --- Mot de passe oublié — étape 1 : vérification numéro + date de naissance ---
def mdp_oublie(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = MotDePasseOublieForm()
    if request.method == 'POST':
        form = MotDePasseOublieForm(request.POST)
        if form.is_valid():
            num = form.cleaned_data['numero_affiliation']
            membre = Membre.objects.get(numero_affiliation=num)
            request.session['reset_membre_id'] = membre.pk
            request.session['reset_membre_nom'] = f"{membre.prenom} {membre.nom}"
            request.session.set_expiry(600)  # 10 minutes
            return redirect('mdp_nouveau')

    return render(request, 'reservations/reset_mdp.html', {'form': form, 'etape': 1})


# --- Mot de passe oublié — étape 2 : nouveau mot de passe ---
def mdp_nouveau(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    membre_id = request.session.get('reset_membre_id')
    if not membre_id:
        messages.error(request, "Session expirée. Recommence depuis le début.")
        return redirect('mdp_oublie')

    membre_nom = request.session.get('reset_membre_nom', '')
    form = NouveauMotDePasseForm()

    if request.method == 'POST':
        form = NouveauMotDePasseForm(request.POST)
        if form.is_valid():
            try:
                membre = Membre.objects.get(pk=membre_id)
            except Membre.DoesNotExist:
                messages.error(request, "Membre introuvable.")
                return redirect('mdp_oublie')

            membre.user.set_password(form.cleaned_data['password1'])
            membre.user.save()

            del request.session['reset_membre_id']
            request.session.pop('reset_membre_nom', None)

            messages.success(request, "Mot de passe réinitialisé avec succès ! Tu peux te connecter.")
            return redirect('login')

    return render(request, 'reservations/reset_mdp.html', {
        'form': form,
        'etape': 2,
        'membre_nom': membre_nom,
    })


@login_required
def dashboard(request):
    """Page d'accueil après connexion — tableau de bord du membre"""
    try:
        membre = Membre.objects.get(user=request.user)
    except Membre.DoesNotExist:
        return redirect('home')

    prochaine_resa = Reserver.objects.filter(
        membres=membre, date__gte=date.today()
    ).order_by('date', 'heure_debut').first()

    nb_resas = Reserver.objects.filter(
        membres=membre, date__gte=date.today()
    ).count()

    return render(request, 'reservations/dashboard.html', {
        'membre': membre,
        'prochaine_resa': prochaine_resa,
        'nb_resas': nb_resas,
        'is_admin': est_admin(request.user),
    })


@login_required
def home(request):
    heures = list(range(9, 23))
    terrains = list(Terrain.objects.all().order_by('numero'))

    # Navigation par date
    date_str = request.GET.get('date')
    if date_str:
        try:
            jour = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            jour = date.today()
    else:
        jour = date.today()

    date_precedente = jour - timedelta(days=1)
    date_suivante = jour + timedelta(days=1)

    # Récupérer le membre connecté (nécessaire pour le bouton annuler)
    try:
        membre = Membre.objects.get(user=request.user)
    except Membre.DoesNotExist:
        membre = None

    # Construire une grille { "terrain_id-heure": {info} }
    grille = {}

    # Réservations
    reservations = Reserver.objects.filter(date=jour).prefetch_related('membres', 'terrain')
    for r in reservations:
        noms = " / ".join([m.nom for m in r.membres.all()])
        nb_joueurs = r.membres.count()
        type_match = "Simple" if nb_joueurs <= 2 else "Double"

        # Vérifier si le membre connecté peut annuler
        peut_annuler = False
        if membre and membre in r.membres.all():
            resa_dt = datetime.combine(r.date, datetime.min.time().replace(hour=r.heure_debut))
            if (resa_dt - datetime.now()).total_seconds() >= 24 * 3600:
                peut_annuler = True

        for offset in range(r.duree):
            h = r.heure_debut + offset
            key = f"{r.terrain.id}-{h}"
            if offset == 0:
                grille[key] = {
                    'statut': 'reserve',
                    'joueurs': noms,
                    'type': type_match,
                    'resa_id': r.id,
                    'peut_annuler': peut_annuler,
                }
            else:
                grille[key] = {
                    'statut': 'reserve_suite',
                    'joueurs': '',
                    'type': f"{type_match} (suite)",
                }

    # Blocages
    blocages_qs = Bloquer.objects.filter(date=jour).select_related('administrateur', 'terrain')
    for b in blocages_qs:
        for offset in range(b.duree):
            h = b.heure_debut + offset
            key = f"{b.terrain.id}-{h}"
            is_entretien = b.raison.lower() == 'entretien'
            grille[key] = {
                'statut': 'entretien' if is_entretien else 'bloque',
                'raison': b.raison,
                'admin': str(b.administrateur),
            }

    # Construire les lignes pour le template
    lignes = []
    for h in heures:
        cases = []
        for t in terrains:
            key = f"{t.id}-{h}"
            info = grille.get(key)
            cases.append({
                'terrain': t,
                'heure': h,
                'info': info,
            })
        lignes.append({'heure': h, 'cases': cases})

    # Afficher la modale de rappel cotisation si le membre n'est pas en ordre
    rappel_cotisation = False
    date_echeance_str = ''
    if membre and not membre.en_ordre_cotisation:
        rappel_cotisation = True
        if membre.date_echeance:
            date_echeance_str = membre.date_echeance.strftime('%d/%m/%Y')
        else:
            date_echeance_str = 'Non payée'

    return render(request, 'reservations/home.html', {
        'terrains': terrains,
        'lignes': lignes,
        'form': ReserverForm(membre_connecte=membre),
        'date_jour': jour,
        'date_precedente': date_precedente,
        'date_suivante': date_suivante,
        'page_active': 'terrains',
        'is_admin': est_admin(request.user),
        'membre': membre,
        'rappel_cotisation': rappel_cotisation,
        'date_echeance_str': date_echeance_str,
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
    })

@login_required
@cotisation_requise
def creer_reservation(request):
    if request.method == 'POST':
        # Récupérer le membre connecté
        try:
            membre = Membre.objects.get(user=request.user)
        except Membre.DoesNotExist:
            messages.error(request, "Ton profil membre est introuvable.")
            return redirect('home')

        form = ReserverForm(request.POST, membre_connecte=membre)
        if form.is_valid():
            duree = form.cleaned_data['duree_calculee']
            type_match = form.cleaned_data['type_match']

            # Créer la réservation principale
            resa = Reserver.objects.create(
                terrain=form.cleaned_data['terrain'],
                date=form.cleaned_data['date'],
                heure_debut=form.cleaned_data['heure_debut'],
                duree=duree,
                statut='reserve',
            )
            resa.membres.set(form.cleaned_data['membres'])
            resa.membres.add(membre)  # Le membre connecté est ajouté automatiquement
            messages.success(request, "Réservation confirmée !")
        else:
            # Afficher les erreurs du formulaire
            for err in form.errors.values():
                messages.error(request, err.as_text())
    return redirect('home')


@login_required
def supprimer_reservation(request, pk):
    resa = get_object_or_404(Reserver, pk=pk)

    # Détecte si la requête vient du JS (appel AJAX) ou d'un lien classique
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Récupérer le membre connecté
    try:
        membre = Membre.objects.get(user=request.user)
    except Membre.DoesNotExist:
        if is_ajax:
            return JsonResponse({'error': 'Profil introuvable.'}, status=404)
        messages.error(request, "Profil introuvable.")
        return redirect('home')

    # Seul un joueur de la réservation peut l'annuler
    if membre not in resa.membres.all():
        if is_ajax:
            return JsonResponse({'error': "Tu ne fais pas partie de cette réservation."}, status=403)
        messages.error(request, "Tu ne fais pas partie de cette réservation.")
        return redirect('home')

    # Vérifier la règle des 24h
    resa_datetime = datetime.combine(resa.date, datetime.min.time().replace(hour=resa.heure_debut))
    maintenant = datetime.now()
    if (resa_datetime - maintenant).total_seconds() < 24 * 3600:
        if is_ajax:
            return JsonResponse({'error': "Impossible d'annuler moins de 24h avant le créneau."}, status=400)
        messages.error(request, "Impossible d'annuler moins de 24h avant le créneau.")
        return redirect('home')

    resa.delete()

    # Réponse JSON si appel AJAX, redirect classique sinon
    if is_ajax:
        return JsonResponse({'success': True, 'message': 'Réservation annulée avec succès.'})

    messages.success(request, "Réservation annulée.")
    return redirect('home')


# ============================================================
#  HELPER : vérifier si le user est un administrateur
# ============================================================
def est_admin(user):
    """Renvoie True si le user connecté est un Administrateur"""
    try:
        membre = Membre.objects.get(user=user)
        return Administrateur.objects.filter(pk=membre.pk).exists()
    except Membre.DoesNotExist:
        return False


# ============================================================
#  PAGES MEMBRES : Annuaire, Mes Réservations, Mon Profil
# ============================================================

# --- Annuaire : liste des membres avec filtres et pagination ---
@login_required
def annuaire(request):
    membres = Membre.objects.all().order_by('nom', 'prenom')

    # Filtre par recherche (nom ou prénom)
    recherche = request.GET.get('q', '')
    if recherche:
        membres = membres.filter(
            Q(nom__icontains=recherche) | Q(prenom__icontains=recherche)
        )

    # Filtre par classement
    classement = request.GET.get('classement', '')
    if classement:
        membres = membres.filter(classement=classement)

    # Filtre par catégorie
    categorie_id = request.GET.get('categorie', '')
    if categorie_id:
        try:
            cat = Categorie.objects.get(pk=categorie_id)
            membres = cat.get_liste_membres()
        except Categorie.DoesNotExist:
            pass

    # Tri
    tri = request.GET.get('tri', 'nom')
    if tri == 'classement':
        membres = membres.order_by('classement', 'nom')

    # Pagination (10 par page)
    paginator = Paginator(membres, 10)
    page = request.GET.get('page')
    membres_page = paginator.get_page(page)

    return render(request, 'reservations/annuaire.html', {
        'membres': membres_page,
        'classements': Membre.CLASSEMENTS,
        'categories': Categorie.objects.all(),
        'recherche': recherche,
        'classement_filtre': classement,
        'categorie_filtre': categorie_id,
        'tri': tri,
        'page_active': 'annuaire',
        'is_admin': est_admin(request.user),
    })


# --- Mes Réservations : liste des résas du membre connecté ---
@login_required
def mes_reservations(request):
    try:
        membre = Membre.objects.get(user=request.user)
    except Membre.DoesNotExist:
        messages.error(request, "Profil introuvable.")
        return redirect('home')

    # Réservations futures et passées
    aujourd_hui = date.today()
    resas_futures = Reserver.objects.filter(
        membres=membre, date__gte=aujourd_hui
    ).order_by('date', 'heure_debut')
    resas_passees = Reserver.objects.filter(
        membres=membre, date__lt=aujourd_hui
    ).order_by('-date', '-heure_debut')

    # Pour chaque résa future, vérifier si on peut annuler (24h avant)
    maintenant = datetime.now()
    for r in resas_futures:
        r.peut_annuler = False
        resa_dt = datetime.combine(r.date, datetime.min.time().replace(hour=r.heure_debut))
        if (resa_dt - maintenant).total_seconds() >= 24 * 3600:
            r.peut_annuler = True

    return render(request, 'reservations/mes_reservations.html', {
        'resas_futures': resas_futures,
        'resas_passees': resas_passees,
        'page_active': 'mes_reservations',
        'is_admin': est_admin(request.user),
    })


# --- Mon Profil : modifier ses coordonnées et son mot de passe ---
@login_required
def mon_profil(request):
    try:
        membre = Membre.objects.get(user=request.user)
    except Membre.DoesNotExist:
        messages.error(request, "Profil introuvable.")
        return redirect('home')

    form_profil = ProfilForm(instance=membre)
    form_mdp = ChangerMotDePasseForm()

    if request.method == 'POST':
        # Détecter quel formulaire a été soumis
        if 'modifier_profil' in request.POST:
            form_profil = ProfilForm(request.POST, instance=membre)
            if form_profil.is_valid():
                try:
                    form_profil.save()
                    messages.success(request, "Profil mis à jour.")
                except Exception:
                    messages.error(request, "Erreur lors de la sauvegarde.")
            else:
                messages.error(request, "Corrige les erreurs dans le formulaire.")

        elif 'changer_mdp' in request.POST:
            form_mdp = ChangerMotDePasseForm(request.POST)
            if form_mdp.is_valid():
                # Vérifier l'ancien mot de passe
                if not request.user.check_password(form_mdp.cleaned_data['ancien']):
                    messages.error(request, "L'ancien mot de passe est incorrect.")
                else:
                    request.user.set_password(form_mdp.cleaned_data['nouveau1'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Mot de passe changé.")
            else:
                for err in form_mdp.errors.values():
                    messages.error(request, err.as_text())

    return render(request, 'reservations/mon_profil.html', {
        'membre': membre,
        'form_profil': form_profil,
        'form_mdp': form_mdp,
        'page_active': 'profil',
        'is_admin': est_admin(request.user),
    })


# ============================================================
#  PAGES ADMIN : Gestion Membres, Terrains, Blocages
# ============================================================

# --- Vérification admin pour toutes les vues admin ---
def admin_requis(view_func):
    """Décorateur simple : vérifie que l'utilisateur est admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not est_admin(request.user):
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


# ===== 1.1 & 1.2 : Activation / Désactivation des membres =====

@admin_requis
def admin_activation_membres(request):
    """Affiche les membres et permet d'activer/désactiver leur cotisation"""
    if request.method == 'POST':
        action = request.POST.get('action')
        ids = request.POST.getlist('membres_ids')

        if not ids:
            messages.error(request, "Sélectionne au moins un membre.")
            return redirect('admin_activation_membres')

        try:
            membres = Membre.objects.filter(pk__in=ids)

            if action == 'activer':
                membres.update(en_ordre_cotisation=True)
                messages.success(request, f"{membres.count()} membre(s) activé(s).")

            elif action == 'desactiver':
                membres.update(en_ordre_cotisation=False)
                messages.success(request, f"{membres.count()} membre(s) désactivé(s).")
        except Exception:
            messages.error(request, "Erreur lors de la modification.")

        return redirect('admin_activation_membres')

    # Séparer actifs et inactifs pour l'affichage
    membres_actifs = Membre.objects.filter(en_ordre_cotisation=True).order_by('nom')
    membres_inactifs = Membre.objects.filter(en_ordre_cotisation=False).order_by('nom')

    return render(request, 'reservations/admin_activation.html', {
        'membres_actifs': membres_actifs,
        'membres_inactifs': membres_inactifs,
    })


# ===== 1.3 : Ajout d'un membre =====

@admin_requis
def admin_ajout_membre(request):
    form = MembreForm()
    if request.method == 'POST':
        form = MembreForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Membre ajouté.")
                return redirect('admin_liste_membres')
            except Exception:
                messages.error(request, "Erreur lors de l'enregistrement.")
        else:
            messages.error(request, "Corrige les erreurs.")

    return render(request, 'reservations/admin_membre_form.html', {
        'form': form,
        'titre': 'Ajouter un membre',
    })


# ===== 1.4 : Modification d'un membre =====

@admin_requis
def admin_modifier_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)
    form = MembreForm(instance=membre)

    if request.method == 'POST':
        form = MembreForm(request.POST, instance=membre)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Membre modifié.")
                return redirect('admin_liste_membres')
            except Exception:
                messages.error(request, "Erreur lors de l'enregistrement.")
        else:
            messages.error(request, "Corrige les erreurs.")

    return render(request, 'reservations/admin_membre_form.html', {
        'form': form,
        'titre': 'Modifier un membre',
        'membre': membre,
    })


# ===== 1.5 : Suppression d'un membre =====

@admin_requis
@require_POST
def admin_supprimer_membre(request, pk):
    membre = get_object_or_404(Membre, pk=pk)

    try:
        # Si le membre a un compte User, on le supprime aussi
        if membre.user:
            membre.user.delete()
        membre.delete()
        messages.success(request, f"{membre} supprimé.")
    except Exception:
        messages.error(request, "Erreur lors de la suppression.")

    return redirect('admin_liste_membres')


# ===== Liste des membres (admin) =====

@admin_requis
def admin_liste_membres(request):
    membres = Membre.objects.all().order_by('nom', 'prenom')

    # Recherche
    q = request.GET.get('q', '')
    if q:
        membres = membres.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(numero_affiliation__icontains=q)
        )

    paginator = Paginator(membres, 15)
    page = request.GET.get('page')
    membres_page = paginator.get_page(page)

    return render(request, 'reservations/admin_liste_membres.html', {
        'membres': membres_page,
        'recherche': q,
    })


# ===== 3.1 : Ajout d'un terrain =====

@admin_requis
def admin_ajout_terrain(request):
    form = TerrainForm()
    if request.method == 'POST':
        form = TerrainForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Terrain ajouté.")
                return redirect('admin_liste_terrains')
            except Exception:
                messages.error(request, "Erreur lors de l'enregistrement.")
        else:
            messages.error(request, "Corrige les erreurs.")

    return render(request, 'reservations/admin_terrain_form.html', {
        'form': form,
        'titre': 'Ajouter un terrain',
    })


# ===== 3.3 : Suppression d'un terrain =====

@admin_requis
@require_POST
def admin_supprimer_terrain(request, pk):
    terrain = get_object_or_404(Terrain, pk=pk)

    # Vérifier s'il y a des réservations futures
    resas_futures = Reserver.objects.filter(terrain=terrain, date__gte=date.today())
    if resas_futures.exists():
        # Supprimer les réservations futures (cas d'utilisation 3.3 - 1.A)
        nb = resas_futures.count()
        resas_futures.delete()
        messages.warning(request, f"{nb} réservation(s) future(s) supprimée(s) avec le terrain.")

    try:
        terrain.delete()
        messages.success(request, f"Terrain {terrain} supprimé.")
    except Exception:
        messages.error(request, "Erreur lors de la suppression.")

    return redirect('admin_liste_terrains')


# ===== Liste des terrains (admin) =====

@admin_requis
def admin_liste_terrains(request):
    terrains = Terrain.objects.all().order_by('numero')
    return render(request, 'reservations/admin_liste_terrains.html', {
        'terrains': terrains,
    })


# ===== 3.2 : Bloquer un terrain =====

@admin_requis
def admin_bloquer_terrain(request):
    form = BloquerForm()
    if request.method == 'POST':
        form = BloquerForm(request.POST)
        if form.is_valid():
            terrain = form.cleaned_data['terrain']
            date_blocage = form.cleaned_data['date']
            heure = form.cleaned_data['heure_debut']
            duree = form.cleaned_data.get('duree', 1)

            # Récupérer l'admin connecté
            try:
                admin_membre = Membre.objects.get(user=request.user)
                admin_obj = Administrateur.objects.get(pk=admin_membre.pk)
            except (Membre.DoesNotExist, Administrateur.DoesNotExist):
                messages.error(request, "Profil admin introuvable.")
                return redirect('admin_bloquer_terrain')

            # Vérifier s'il y a des réservations en conflit (cas 3.2 - 1.A)
            conflits = Reserver.objects.filter(
                terrain=terrain,
                date=date_blocage,
                heure_debut__lt=heure + duree,
                heure_debut__gt=heure - F('duree'),
            )
            if conflits.exists():
                nb = conflits.count()
                conflits.delete()
                messages.warning(request, f"{nb} réservation(s) en conflit supprimée(s).")

            try:
                Bloquer.objects.create(
                    terrain=terrain,
                    date=date_blocage,
                    heure_debut=heure,
                    duree=duree,
                    statut='bloque',
                    administrateur=admin_obj,
                    raison=form.cleaned_data['raison'],
                )
                messages.success(request, "Terrain bloqué.")
                return redirect('home')
            except Exception:
                messages.error(request, "Erreur lors du blocage.")
        else:
            messages.error(request, "Corrige les erreurs.")

    return render(request, 'reservations/admin_bloquer.html', {
        'form': form,
    })


# ===== Admin : supprimer une réservation (pas de contrainte 24h) =====

@admin_requis
def admin_supprimer_reservation(request, pk):
    resa = get_object_or_404(Reserver, pk=pk)
    try:
        resa.delete()
        messages.success(request, "Réservation supprimée par l'admin.")
    except Exception:
        messages.error(request, "Erreur lors de la suppression.")
    return redirect('home')


# ============================================================
#  GOOGLE AUTH : lier le compte Google au membre
# ============================================================

@login_required
@require_POST
def google_auth(request):
    """Reçoit l'email Google via AJAX et le stocke dans le profil du membre"""
    try:
        if request.content_type == 'application/json':
            body = json.loads(request.body)
            google_email = body.get('email', '')
        else:
            google_email = request.POST.get('email', '')

        if not google_email:
            return JsonResponse({'error': 'Email manquant'}, status=400)

        membre = Membre.objects.get(user=request.user)
        membre.google_email = google_email
        membre.save()

        return JsonResponse({'success': True, 'email': google_email})

    except Membre.DoesNotExist:
        return JsonResponse({'error': 'Profil introuvable'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données invalides'}, status=400)


# ============================================================
#  STRIPE : créer une session de paiement pour la cotisation
# ============================================================

@login_required
def creer_session_paiement(request):
    """Crée une session Stripe Checkout et redirige le membre vers la page de paiement"""
    try:
        membre = Membre.objects.get(user=request.user)

        # Utiliser l'email du compte utilisateur
        email_paiement = request.user.email

        # Créer la session Stripe Checkout
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Cotisation Tennis Club',
                        'description': f'Cotisation annuelle - {membre.prenom} {membre.nom}',
                    },
                    'unit_amount': 50000,  # 50 euros 
                },
                'quantity': 1,
            }],
            mode='payment',
            # Passer l'id du membre pour le retrouver dans le webhook
            client_reference_id=str(membre.pk),
            customer_email=email_paiement,
            success_url=request.build_absolute_uri('/paiement/succes/'),
            cancel_url=request.build_absolute_uri('/paiement/annule/'),
        )
        return redirect(session.url)

    except Membre.DoesNotExist:
        messages.error(request, "Profil introuvable.")
        return redirect('home')
    except stripe.error.StripeError as e:
        messages.error(request, f"Erreur Stripe : {str(e)}")
        return redirect('home')


# ============================================================
#  STRIPE WEBHOOK : confirmation automatique du paiement
# ============================================================

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Reçoit les événements Stripe et met à jour le statut du membre"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

  
    if settings.DEBUG and not sig_header:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Payload invalide'}, status=400)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return JsonResponse({'error': 'Payload invalide'}, status=400)
        except stripe.error.SignatureVerificationError:
            return JsonResponse({'error': 'Signature invalide'}, status=400)

    # Traiter l'événement de paiement réussi
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        membre_id = session.get('client_reference_id')

        if membre_id:
            try:
                membre = Membre.objects.get(pk=membre_id)
                # Paiement confirmé : on active la cotisation
                membre.en_ordre_cotisation = True
                membre.date_echeance = date(date.today().year, 12, 31)
                membre.date_dernier_paiement = timezone.now()
                membre.save()
            except Membre.DoesNotExist:
                pass

    return JsonResponse({'status': 'ok'})


# === Pages de retour après paiement Stripe ===

@login_required
def paiement_succes(request):
    try:
        membre = Membre.objects.get(user=request.user)
        membre.en_ordre_cotisation = True
        membre.date_dernier_paiement = timezone.now()
        membre.date_echeance = date.today() + timedelta(days=365)
        membre.save()
    except Membre.DoesNotExist:
        pass
    messages.success(request, "Paiement réussi ! Ta cotisation est maintenant en ordre.")
    return redirect('home')


@login_required
def paiement_annule(request):
    messages.warning(request, "Paiement annulé. Tu peux réessayer quand tu veux.")
    return redirect('home')


# ============================================================
#  API AJAX : recherche annuaire en temps réel (programmation asynchrone)
# ============================================================

@login_required
def api_recherche_annuaire(request):
    """API JSON pour la recherche en live dans l'annuaire (appelée en AJAX via fetch)"""
    q = request.GET.get('q', '')
    classement = request.GET.get('classement', '')

    membres = Membre.objects.all().order_by('nom', 'prenom')

    # Filtre par recherche (nom ou prénom)
    if q:
        membres = membres.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q)
        )

    # Filtre par classement
    if classement:
        membres = membres.filter(classement=classement)

    # Limiter à 20 résultats pour les performances
    membres = membres[:20]

    # Construire la réponse JSON
    resultats = []
    for m in membres:
        resultats.append({
            'nom': m.nom,
            'prenom': m.prenom,
            'classement': m.classement,
            'sexe': m.sexe,
            'localite': m.localite,
            'en_ordre': m.en_ordre_cotisation,
        })

    return JsonResponse({'membres': resultats})


# ============================================================
#  API AJAX : vérifier si un créneau est encore disponible
# ============================================================

@login_required
def api_disponibilite(request):
    """Vérifie en temps réel si un terrain est libre pour un créneau donné"""
    terrain_id = request.GET.get('terrain')
    date_str = request.GET.get('date')
    heure = request.GET.get('heure')

    # Paramètres manquants : on dit disponible par défaut
    if not terrain_id or not date_str or not heure:
        return JsonResponse({'disponible': True})

    try:
        # Cherche une réservation existante sur ce terrain, ce jour, à cette heure
        deja_pris = Reserver.objects.filter(
            terrain_id=terrain_id,
            date=date_str,
            heure_debut=int(heure)
        ).exists()
        return JsonResponse({'disponible': not deja_pris})
    except Exception:
        # En cas d'erreur inattendue, on laisse la modale s'ouvrir quand même
        return JsonResponse({'disponible': True})