from datetime import timedelta
import os
from pathlib import Path
import dj_database_url
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", 'django-insecure-nice_key')

MODE = os.getenv("MODE")
DEBUG = os.getenv("DEBUG", "False") == "True"
APPEND_SLASH=False
BROKER_URL = os.getenv("BROKER_URL", "amqp://rafaelbochi:2012@localhost/fabricapainel")
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    # Subdomínios de fexcompany.me
    "https://*.fexcompany.me",
    # Subdomínios de fabricadesoftware.ifc.edu.br
    "https://*.fabricadesoftware.ifc.edu.br",
    # Front-end local
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:3000",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Frontend em desenvolvimento
    "http://localhost:3000",
    "https://*.fexcompany.me",
    "https://*.fabricadesoftware.ifc.edu.br",
]

# Permitir cookies nas requisições cross-origin
CORS_ALLOW_CREDENTIALS = True

# Permitir todos os métodos HTTP
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# Permitir todos os headers
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "safedelete",
    "corsheaders",
    "simple_history",
    "drf_spectacular",
    "django_celery_beat",
    "django_filters",
    "rest_framework",
    'rest_framework_simplejwt',
    "debug_toolbar",
    "src.core.user.infra.user_django_app",
    "src.core.control_Id.infra.control_id_django_app",
    "src.core.control_id_config.infra.control_id_config_django_app",
    # Celery results backend via django-celery-results (opcional)
    "django_celery_results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = 'django_project.urls'

AUTH_USER_MODEL = "user_django_app.User"

SAFE_DELETE_FIELD_NAME = "deleted_at"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # 'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    "DEFAULT_PAGINATION_CLASS": "src.core.__seedwork__.infra.pagination.CustomPageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Fabrica Painel API",
    "DESCRIPTION": "API para gerenciamento do Fabrica Painel, incluindo endpoints e documentação.",
    "VERSION": "1.0.0",
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "templates")
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_project.context_processors.admin_dashboard',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INTERNAL_IPS = ["127.0.0.1", "localhost", "0.0.0.0"]

CATRAKA_URL = os.getenv("CATRAKA_URL", 'http://localhost:8080')
CATRAKA_USER = os.getenv("CATRAKA_USER", 'nice_user')
CATRAKA_PASS = os.getenv("CATRAKA_PASS", 'nice_pass')

CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_BACKEND = "rpc://"
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', BROKER_URL)