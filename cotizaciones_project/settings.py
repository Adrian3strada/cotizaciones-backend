import os
import sys
import warnings
from decimal import Decimal

warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*", module="requests")
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

_secret = os.environ.get("SECRET_KEY")
if not _secret and os.environ.get("DEBUG", "True") == "False":
    raise ValueError(
        "SECRET_KEY debe definirse en producción. "
        "Ej: export SECRET_KEY='$(python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\")'"
    )
SECRET_KEY = _secret or "django-insecure-dev-only-change-in-production"

DEBUG = os.environ.get("DEBUG", "True") == "True"

def _running_tests():
    if os.environ.get("DJANGO_RUNNING_TESTS", "").lower() in ("1", "true", "yes"):
        return True
    return len(sys.argv) > 1 and sys.argv[1] == "test"

_allowed_hosts_env = os.environ.get("ALLOWED_HOSTS")
if _allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(",") if host.strip()]
else:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".railway.app", ".up.railway.app"]

_railway_public = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_APP_DOMAIN")
if _railway_public:
    _host = _railway_public.strip().replace("https://", "").replace("http://", "").rstrip("/")
    if _host and _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

_contabo_domain = os.environ.get("CONTABO_DOMAIN")
if _contabo_domain:
    for d in _contabo_domain.split(","):
        d = d.strip()
        if d and d not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(d)

_ngrok_hosts = os.environ.get("NGROK_HOSTS")
if _ngrok_hosts:
    for h in _ngrok_hosts.split(","):
        h = h.strip()
        if h and h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

_csrf_trusted_origins_env = os.environ.get("CSRF_TRUSTED_ORIGINS")
if _csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in _csrf_trusted_origins_env.split(",")
        if origin.strip()
    ]
else:
    CSRF_TRUSTED_ORIGINS = []

_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_APP_DOMAIN")
if _railway_domain:
    _domain = _railway_domain.strip().replace("https://", "").replace("http://", "").rstrip("/")
    for _scheme in ("https", "http"):
        _origin = f"{_scheme}://{_domain}"
        if _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [_origin]

if _ngrok_hosts:
    for h in _ngrok_hosts.split(","):
        h = h.strip()
        if h:
            _origin = f"https://{h}" if not h.startswith("http") else h
            if _origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [_origin]

if _contabo_domain:
    for d in _contabo_domain.split(","):
        d = d.strip()
        if d:
            _origin = f"https://{d}"
            if _origin not in CSRF_TRUSTED_ORIGINS:
                CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [_origin]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'django_filters',
    'customers',
    'catalog',
    'accounts',
    'quotes.apps.QuotesConfig',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cotizaciones_project.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'cotizaciones_project.wsgi.application'

_database_url = os.environ.get("DATABASE_URL")
if _database_url:

    _parsed = urlparse(_database_url)
    _db_name = _parsed.path.lstrip("/")
    if _parsed.scheme == "postgres":
        _parsed = _parsed._replace(scheme="postgresql")

    _db_host = (_parsed.hostname or "").lower()
    _ssl_mode = os.environ.get("DATABASE_SSL_MODE")
    if _ssl_mode is None and _db_host in ("localhost", "127.0.0.1", ""):
        _ssl_mode = "disable"
    elif _ssl_mode is None:
        _ssl_mode = "require"
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_name,
            "USER": _parsed.username,
            "PASSWORD": _parsed.password,
            "HOST": _parsed.hostname,
            "PORT": _parsed.port or "5432",
            "OPTIONS": {"sslmode": _ssl_mode},
        }
    }
elif os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE"),
            "USER": os.environ.get("POSTGRES_USER") or os.environ.get("PGUSER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST") or os.environ.get("PGHOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT") or os.environ.get("PGPORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = "es"

TIME_ZONE = "America/Mexico_City"

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if _running_tests()
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'quotes:dashboard'
LOGOUT_REDIRECT_URL = 'login'

if not DEBUG:
    _tests = _running_tests()
    SESSION_COOKIE_SECURE = not _tests
    CSRF_COOKIE_SECURE = not _tests

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

    SECURE_SSL_REDIRECT = (not _tests) and (
        os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
    )

    _hsts = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    if _hsts > 0:
        SECURE_HSTS_SECONDS = _hsts
        SECURE_HSTS_INCLUDE_SUBDOMAINS = (
            os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
        )
        SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "False") == "True"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

    X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

_session_age = os.environ.get("SESSION_COOKIE_AGE")
if _session_age is not None:
    try:
        SESSION_COOKIE_AGE = max(300, int(_session_age))
    except ValueError:
        pass

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_drf_auth = [
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.SessionAuthentication",
]
if DEBUG or os.environ.get("DRF_ALLOW_BASIC_AUTH", "False") == "True":
    _drf_auth.append("rest_framework.authentication.BasicAuthentication")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": _drf_auth,
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

QUOTE_DEFAULT_USD_MXN_RATE = Decimal(os.environ.get("QUOTE_DEFAULT_USD_MXN_RATE", "20.00"))

QUOTE_PDF_ENGINE = os.environ.get("QUOTE_PDF_ENGINE", "reportlab")

QUOTE_PDF_HEADER_IMAGE = os.environ.get("QUOTE_PDF_HEADER_IMAGE", "img/quote_header_right.png")

QUOTE_PDF_COMPANY = {
    "name": os.environ.get("QUOTE_PDF_COMPANY_NAME", "Sistemas de Conteo de Personas."),
    "website": os.environ.get("QUOTE_PDF_COMPANY_WEBSITE", "www.sisconper.com"),
    "street": os.environ.get(
        "QUOTE_PDF_COMPANY_STREET",
        "Blvd. Paseo de la Rep├║blica No. 13020 Int. 1307",
    ),
    "colony": os.environ.get("QUOTE_PDF_COMPANY_COLONY", "Col. Juriquilla, Quer├⌐taro, Qro."),
    "postal_code": os.environ.get("QUOTE_PDF_COMPANY_POSTAL_CODE", "C.P. 76230"),
    "phone": os.environ.get("QUOTE_PDF_COMPANY_PHONE", "(442) 245 7000"),
    "mobile": os.environ.get("QUOTE_PDF_COMPANY_MOBILE", ""),
    "rfc": os.environ.get("QUOTE_PDF_COMPANY_RFC", "SCP070410C43"),
    "email": os.environ.get("QUOTE_PDF_COMPANY_EMAIL", "info@sisconper.com"),
}

QUOTE_PDF_AUTHORIZED = os.environ.get("QUOTE_PDF_AUTHORIZED", "Carlos Medina")

QUOTE_PDF_PAYMENT_FORM = os.environ.get("QUOTE_PDF_PAYMENT_FORM", "")
QUOTE_PDF_DELIVERY_TIME = os.environ.get("QUOTE_PDF_DELIVERY_TIME", "")
QUOTE_PDF_WARRANTY = os.environ.get("QUOTE_PDF_WARRANTY", "")
QUOTE_PDF_DELIVERY_PLACE = os.environ.get("QUOTE_PDF_DELIVERY_PLACE", "")

SPECTACULAR_SETTINGS = {
    "TITLE": "Cotizaciones API",
    "DESCRIPTION": "API REST para integraci├│n con ERP/CRM. Cotizaciones, clientes y cat├ílogo.",
    "VERSION": "1.0.0",
}
