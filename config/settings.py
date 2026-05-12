from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure--k_i&!y&^9f^x_+qe+&bea!2)m+d%%kgy$57%s*ds5la6reo1^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reservations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'reservations.context_processors.membre_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database (PostgreSQL configuré)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'TennisDB',
        'USER': 'postgres',
        'PASSWORD': 'Ahlemmarwa@140', 
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization (Passage en Français)
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redirections
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# --- STRIPE (clés de test pour le paiement cotisation) ---
STRIPE_PUBLIC_KEY = 'pk_test_51TMPg70sEnFCNif2ugWGzsujpFOc6GGkG2uZYtrE5QE1zSYBTz78LRmIzDBCBm4b9jBLnurLISYgoX9isTO95fUN00CJydlp9t'
STRIPE_SECRET_KEY = 'sk_test_51TMPg70sEnFCNif2dP71yV0N00wVdTLYTxPpaCVrmaWXkuoo32taFyFKWmMVIiCOOTn5fvX8YKgJ0kJyucL7cBL100KXb9S0l3'
STRIPE_WEBHOOK_SECRET = 'whsec_VOTRE_WEBHOOK_SECRET'

# --- GOOGLE IDENTITY SERVICES (authentification Google pour lier le compte) ---
GOOGLE_CLIENT_ID = '311791709280-q8uf3gjbvf1k0de92bh8j66479itae7e.apps.googleusercontent.com'

# Headers de protection
SECURE_BROWSER_XSS_FILTER = True

# --- EMAIL (Gmail SMTP) ---
# IMPORTANT : utiliser un "Mot de passe d'application" Google (16 caractères),
# pas le mot de passe normal. Activer d'abord la vérification en 2 étapes sur
# myaccount.google.com → Sécurité → Mots de passe des applications.
PASSWORD_RESET_TIMEOUT = 86400  # pour la production (email)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Permettre au popup Google Sign-In de communiquer avec la page parente
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"