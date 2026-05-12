from django.test import TestCase, Client
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
from .models import Membre, Administrateur, Terrain, Reserver, Bloquer, Categorie


class MembreModelTest(TestCase):
    """Tests sur le modèle Membre"""

    def setUp(self):
        self.membre = Membre.objects.create(
            numero_affiliation='1234567',
            nom='Dupont', prenom='Jean',
            rue='Rue de la Gare 1', code_postal='1000',
            localite='Bruxelles', gsm='0470000000',
            email='jean@test.com', classement='C30',
            sexe='M', date_naissance=date(1990, 5, 15),
            en_ordre_cotisation=True,
        )

    def test_str(self):
        self.assertEqual(str(self.membre), "Jean Dupont")

    def test_get_age(self):
        age = self.membre.get_age()
        attendu = date.today().year - 1990
        if (date.today().month, date.today().day) < (5, 15):
            attendu -= 1
        self.assertEqual(age, attendu)

    def test_numero_affiliation_unique(self):
        with self.assertRaises(Exception):
            Membre.objects.create(
                numero_affiliation='1234567',
                nom='Martin', prenom='Alice',
                rue='Rue Test', code_postal='2000',
                localite='Liège', gsm='0471111111',
                email='alice@test.com', classement='N.C',
                sexe='F', date_naissance=date(1995, 1, 1),
            )


class TerrainModelTest(TestCase):
    """Tests sur le modèle Terrain"""

    def setUp(self):
        self.terrain = Terrain.objects.create(numero=1, surface='Terre Battue')

    def test_str(self):
        self.assertEqual(str(self.terrain), "Court 1")

    def test_numero_unique(self):
        with self.assertRaises(Exception):
            Terrain.objects.create(numero=1, surface='Gazon')


class CategorieModelTest(TestCase):
    """Tests sur le modèle Categorie"""

    def setUp(self):
        self.cat = Categorie.objects.create(
            nom='Messieurs', age_min=18, age_max=99, sexe='M'
        )
        self.membre = Membre.objects.create(
            numero_affiliation='2000001',
            nom='Test', prenom='Homme',
            rue='Rue X', code_postal='1000',
            localite='Bxl', gsm='0470000001',
            email='homme@test.com', classement='N.C',
            sexe='M', date_naissance=date(1990, 1, 1),
        )

    def test_get_liste_membres(self):
        membres = self.cat.get_liste_membres()
        self.assertIn(self.membre, membres)

    def test_get_categories_membre(self):
        cats = self.membre.get_categories()
        self.assertIn(self.cat, cats)


class ConnexionTest(TestCase):
    """Tests sur la connexion par numéro d'affiliation"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='1234567', password='testpass123'
        )
        self.membre = Membre.objects.create(
            user=self.user,
            numero_affiliation='1234567',
            nom='Dupont', prenom='Jean',
            rue='Rue Test', code_postal='1000',
            localite='Bruxelles', gsm='0470000000',
            email='jean@test.com', classement='C30',
            sexe='M', date_naissance=date(1990, 5, 15),
            en_ordre_cotisation=True,
        )

    def test_login_valide(self):
        resp = self.client.post('/login/', {
            'numero_affiliation': '1234567',
            'password': 'testpass123',
        })
        self.assertEqual(resp.status_code, 302)

    def test_login_mauvais_mdp(self):
        resp = self.client.post('/login/', {
            'numero_affiliation': '1234567',
            'password': 'mauvais',
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_numero_inexistant(self):
        resp = self.client.post('/login/', {
            'numero_affiliation': '9999999',
            'password': 'testpass123',
        })
        self.assertEqual(resp.status_code, 200)

    def test_redirection_si_connecte(self):
        self.client.login(username='1234567', password='testpass123')
        resp = self.client.get('/login/')
        self.assertEqual(resp.status_code, 302)


class PremiereConnexionTest(TestCase):
    """Tests sur la première connexion (création du mot de passe)"""

    def setUp(self):
        self.client = Client()
        self.membre = Membre.objects.create(
            numero_affiliation='3000001',
            nom='Nouveau', prenom='Membre',
            rue='Rue Neuve', code_postal='1000',
            localite='Bruxelles', gsm='0470000002',
            email='nouveau@test.com', classement='N.C',
            sexe='M', date_naissance=date(2000, 1, 1),
        )

    def test_creation_compte(self):
        resp = self.client.post('/premiere-connexion/', {
            'numero_affiliation': '3000001',
            'password1': 'monmdp123',
            'password2': 'monmdp123',
        })
        self.assertEqual(resp.status_code, 302)
        self.membre.refresh_from_db()
        self.assertIsNotNone(self.membre.user)

    def test_mdp_different(self):
        resp = self.client.post('/premiere-connexion/', {
            'numero_affiliation': '3000001',
            'password1': 'monmdp123',
            'password2': 'autremdp1',
        })
        self.assertEqual(resp.status_code, 200)


class ReservationTest(TestCase):
    """Tests sur la création et l'annulation de réservations"""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='1000001', password='pass1234')
        self.user2 = User.objects.create_user(username='1000002', password='pass1234')

        self.terrain = Terrain.objects.create(numero=1, surface='Terre Battue')

        self.m1 = Membre.objects.create(
            user=self.user1, numero_affiliation='1000001',
            nom='Joueur', prenom='Un',
            rue='R1', code_postal='1000', localite='Bxl',
            gsm='0470000010', email='j1@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1990, 1, 1),
            en_ordre_cotisation=True,
        )
        self.m2 = Membre.objects.create(
            user=self.user2, numero_affiliation='1000002',
            nom='Joueur', prenom='Deux',
            rue='R2', code_postal='1000', localite='Bxl',
            gsm='0470000011', email='j2@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1992, 1, 1),
            en_ordre_cotisation=True,
        )

        # Date future pour les tests
        self.date_future = date.today() + timedelta(days=7)

    def test_creer_reservation_simple(self):
        self.client.login(username='1000001', password='pass1234')
        resp = self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 10,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Reserver.objects.count(), 1)
        resa = Reserver.objects.first()
        self.assertIn(self.m1, resa.membres.all())
        self.assertIn(self.m2, resa.membres.all())

    def test_reservation_dans_le_passe(self):
        self.client.login(username='1000001', password='pass1234')
        hier = date.today() - timedelta(days=1)
        resp = self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': hier.isoformat(),
            'heure_debut': 10,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 0)

    def test_reservation_hors_plage_horaire(self):
        self.client.login(username='1000001', password='pass1234')
        resp = self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 22,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 0)

    def test_conflit_terrain(self):
        """Deux réservations sur le même terrain au même créneau"""
        self.client.login(username='1000001', password='pass1234')
        self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 14,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 1)

        # Deuxième sur le même créneau avec d'autres joueurs
        user3 = User.objects.create_user(username='1000003', password='pass1234')
        m3 = Membre.objects.create(
            user=user3, numero_affiliation='1000003',
            nom='Joueur', prenom='Trois',
            rue='R3', code_postal='1000', localite='Bxl',
            gsm='0470000012', email='j3@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1991, 1, 1),
            en_ordre_cotisation=True,
        )
        user4 = User.objects.create_user(username='1000004', password='pass1234')
        m4 = Membre.objects.create(
            user=user4, numero_affiliation='1000004',
            nom='Joueur', prenom='Quatre',
            rue='R4', code_postal='1000', localite='Bxl',
            gsm='0470000013', email='j4@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1993, 1, 1),
            en_ordre_cotisation=True,
        )
        self.client.login(username='1000003', password='pass1234')
        self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 14,
            'type_match': 'simple',
            'membres': [m4.pk],
        })
        self.assertEqual(Reserver.objects.count(), 1)

    def test_annulation_24h(self):
        """On ne peut pas annuler une réservation à moins de 24h"""
        self.client.login(username='1000001', password='pass1234')
        demain = date.today() + timedelta(days=1)
        resa = Reserver.objects.create(
            terrain=self.terrain, date=demain,
            heure_debut=9, duree=1, statut='reserve',
        )
        resa.membres.add(self.m1, self.m2)

        now = datetime.now()
        resa_dt = datetime.combine(demain, datetime.min.time().replace(hour=9))
        if (resa_dt - now).total_seconds() < 24 * 3600:
            resp = self.client.get(f'/supprimer-reservation/{resa.pk}/')
            self.assertEqual(Reserver.objects.count(), 1)

    def test_annulation_plus_de_24h(self):
        """On peut annuler une réservation à plus de 24h"""
        self.client.login(username='1000001', password='pass1234')
        dans_3j = date.today() + timedelta(days=3)
        resa = Reserver.objects.create(
            terrain=self.terrain, date=dans_3j,
            heure_debut=10, duree=1, statut='reserve',
        )
        resa.membres.add(self.m1, self.m2)

        resp = self.client.get(f'/supprimer-reservation/{resa.pk}/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Reserver.objects.count(), 0)

    def test_cotisation_requise(self):
        """Un membre pas en ordre ne peut pas réserver"""
        self.m1.en_ordre_cotisation = False
        self.m1.save()
        self.client.login(username='1000001', password='pass1234')
        resp = self.client.post('/reserver/', {
            'terrain': self.terrain.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 10,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 0)


class QuotaHebdoTest(TestCase):
    """Tests sur les quotas hebdomadaires"""

    def setUp(self):
        self.client = Client()
        self.terrain1 = Terrain.objects.create(numero=1, surface='Terre Battue')
        self.terrain2 = Terrain.objects.create(numero=2, surface='Terre Battue')
        self.terrain3 = Terrain.objects.create(numero=3, surface='Terre Battue')

        self.user1 = User.objects.create_user(username='2000001', password='pass1234')
        self.user2 = User.objects.create_user(username='2000002', password='pass1234')

        self.m1 = Membre.objects.create(
            user=self.user1, numero_affiliation='2000001',
            nom='Quota', prenom='Test',
            rue='R1', code_postal='1000', localite='Bxl',
            gsm='0470000020', email='q1@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1990, 1, 1),
            en_ordre_cotisation=True,
        )
        self.m2 = Membre.objects.create(
            user=self.user2, numero_affiliation='2000002',
            nom='Partenaire', prenom='Quota',
            rue='R2', code_postal='1000', localite='Bxl',
            gsm='0470000021', email='q2@test.com',
            classement='C30', sexe='M',
            date_naissance=date(1992, 1, 1),
            en_ordre_cotisation=True,
        )

        self.date_future = date.today() + timedelta(days=7)

    def test_max_2h_simple(self):
        """Max 2h de simple par semaine"""
        self.client.login(username='2000001', password='pass1234')

        # 1ère heure simple
        self.client.post('/reserver/', {
            'terrain': self.terrain1.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 10,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        # 2ème heure simple
        self.client.post('/reserver/', {
            'terrain': self.terrain2.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 11,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 2)

        # 3ème heure simple = refusée
        self.client.post('/reserver/', {
            'terrain': self.terrain3.pk,
            'date': self.date_future.isoformat(),
            'heure_debut': 12,
            'type_match': 'simple',
            'membres': [self.m2.pk],
        })
        self.assertEqual(Reserver.objects.count(), 2)


class AdminTest(TestCase):
    """Tests sur les fonctions d'administration"""

    def setUp(self):
        self.client = Client()
        self.user_admin = User.objects.create_user(
            username='9000001', password='admin123'
        )
        self.admin_membre = Administrateur.objects.create(
            user=self.user_admin, numero_affiliation='9000001',
            nom='Admin', prenom='Test',
            rue='Rue Admin', code_postal='1000',
            localite='Bruxelles', gsm='0470000099',
            email='admin@test.com', classement='C15',
            sexe='M', date_naissance=date(1985, 3, 20),
            en_ordre_cotisation=True,
        )
        self.terrain = Terrain.objects.create(numero=1, surface='Terre Battue')

    def test_acces_admin_si_admin(self):
        self.client.login(username='9000001', password='admin123')
        resp = self.client.get('/gestion/membres/')
        self.assertEqual(resp.status_code, 200)

    def test_acces_admin_refuse_si_membre(self):
        user = User.objects.create_user(username='8000001', password='pass1234')
        Membre.objects.create(
            user=user, numero_affiliation='8000001',
            nom='Membre', prenom='Normal',
            rue='Rue X', code_postal='1000',
            localite='Bxl', gsm='0470000088',
            email='normal@test.com', classement='N.C',
            sexe='M', date_naissance=date(1995, 1, 1),
            en_ordre_cotisation=True,
        )
        self.client.login(username='8000001', password='pass1234')
        resp = self.client.get('/gestion/membres/')
        self.assertEqual(resp.status_code, 302)

    def test_activation_membre(self):
        user = User.objects.create_user(username='8000002', password='pass1234')
        m = Membre.objects.create(
            user=user, numero_affiliation='8000002',
            nom='Inactif', prenom='Test',
            rue='Rue Y', code_postal='1000',
            localite='Bxl', gsm='0470000087',
            email='inactif@test.com', classement='N.C',
            sexe='M', date_naissance=date(1995, 1, 1),
            en_ordre_cotisation=False,
        )
        self.client.login(username='9000001', password='admin123')
        resp = self.client.post('/gestion/membres/activation/', {
            'action': 'activer',
            'membres_ids': [m.pk],
        })
        m.refresh_from_db()
        self.assertTrue(m.en_ordre_cotisation)

    def test_bloquer_terrain(self):
        self.client.login(username='9000001', password='admin123')
        resp = self.client.post('/gestion/bloquer/', {
            'terrain': self.terrain.pk,
            'date': (date.today() + timedelta(days=5)).isoformat(),
            'heure_debut': 14,
            'duree': 1,
            'raison': 'Entretien',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Bloquer.objects.count(), 1)


class AnnuaireTest(TestCase):
    """Tests sur l'annuaire et la recherche AJAX"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='7000001', password='pass1234')
        Membre.objects.create(
            user=self.user, numero_affiliation='7000001',
            nom='Recherche', prenom='Test',
            rue='Rue Z', code_postal='1000',
            localite='Bxl', gsm='0470000077',
            email='rech@test.com', classement='C30',
            sexe='M', date_naissance=date(1990, 1, 1),
            en_ordre_cotisation=True,
        )

    def test_annuaire_accessible(self):
        self.client.login(username='7000001', password='pass1234')
        resp = self.client.get('/annuaire/')
        self.assertEqual(resp.status_code, 200)

    def test_api_recherche_json(self):
        self.client.login(username='7000001', password='pass1234')
        resp = self.client.get('/api/annuaire/?q=Recherche')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['membres']), 1)
        self.assertEqual(data['membres'][0]['nom'], 'Recherche')

    def test_api_recherche_vide(self):
        self.client.login(username='7000001', password='pass1234')
        resp = self.client.get('/api/annuaire/?q=Introuvable')
        data = resp.json()
        self.assertEqual(len(data['membres']), 0)
