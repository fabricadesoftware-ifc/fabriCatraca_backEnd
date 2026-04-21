from datetime import timedelta
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent



def show_toolbar(request):
    return DEBUG

SECRET_KEY = os.getenv("SECRET_KEY", 'django-insecure-nice_key')

MODE = os.getenv("MODE")
DEBUG = os.getenv("DEBUG", "False") == "True"
APPEND_SLASH=False
BROKER_URL = os.getenv("BROKER_URL", "amqp://rafaelbochi:2012@localhost/fabricapainel")
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    "https://catraca.fabricadesoftware.ifc.edu.br",
    "http://localhost:3000",
]

CORS_ALLOWED_ORIGINS = [
    "https://catraca.fabricadesoftware.ifc.edu.br",
    "http://localhost:3000",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # novo padrão
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # lê senhas antigas
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
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
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "safedelete",
    "corsheaders",
    "simple_history",
    "drf_spectacular",
    "django_celery_beat",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_extensions",
    "minio_storage",
    "src.core.user.infra.user_django_app",
    "src.core.control_Id.infra.control_id_django_app",
    "src.core.control_id_config.infra.control_id_config_django_app",
    "src.core.control_id_monitor.infra.control_id_monitor_django_app",
    "src.core.uploader",
    "django_celery_results",
    "debug_toolbar",
    "axes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "axes.middleware.AxesMiddleware",
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
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
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
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django_project.context_processors.admin_dashboard",
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

AXES_FAILURE_LIMIT = 7  # bloqueia após 5 tentativas falhas
AXES_COOLOFF_TIME = 1  # bloqueia por 1 hora
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]  # bloqueia por IP + usuário
NUM_PROXIES = 1
USE_X_FORWARDED_HOST = True

AXES_PROXY_COUNT = 1
AXES_META_PRECEDENCE_ORDER = [
    "HTTP_X_FORWARDED_FOR",
    "REMOTE_ADDR",
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
AXES_ENABLED = False


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INTERNAL_IPS = ['*', '127.0.0.1', 'localhost', '0.0.0.0', '172.16.0.1']

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "src.django_project.settings.show_toolbar",
}

CATRAKA_URL = os.getenv("CATRAKA_URL", 'http://localhost:8080')
CATRAKA_USER = os.getenv("CATRAKA_USER", 'nice_user')
CATRAKA_PASS = os.getenv("CATRAKA_PASS", 'nice_pass')
TEMPORARY_RELEASE_ACCESS_RULE_ID = os.getenv("TEMPORARY_RELEASE_ACCESS_RULE_ID", 1)
TEMPORARY_RELEASE_TASK_INTERVAL_SECONDS = os.getenv(
    "TEMPORARY_RELEASE_TASK_INTERVAL_SECONDS",
    15,
)
TEMPORARY_RELEASE_DELAY_ALERT_SECONDS = os.getenv(
    "TEMPORARY_RELEASE_DELAY_ALERT_SECONDS",
    300,
)
MONITOR_OFFLINE_CHECK_INTERVAL_SECONDS = os.getenv(
    "MONITOR_OFFLINE_CHECK_INTERVAL_SveECONDS",
    60,
)
IFC_SCHEDULES_SOURCE_URL = os.getenv(
    "IFC_SCHEDULES_SOURCE_URL",
    "https://horarios.araquari.ifc.edu.br/data/horario2026.29_mar%C3%A7o_years_days_horizontal.html",
)

CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_BACKEND = "rpc://"
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', BROKER_URL)
CELERY_BEAT_SCHEDULE = {
    "reconcile_temporary_releases": {
        "task": "src.core.control_Id.infra.control_id_django_app.tasks.reconcile_temporary_releases",
        "schedule": 600,  # safety net a cada 10 min
    },
    "check_monitor_heartbeats": {
        "task": "src.core.control_id_monitor.infra.control_id_monitor_django_app.tasks.check_monitor_heartbeats",
        "schedule": MONITOR_OFFLINE_CHECK_INTERVAL_SECONDS,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # mantém loggers já existentes
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",  # mostra tudo no console
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",  # define nível global
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",  # reduz verbosidade do Django core
            "propagate": False,
        },
        # logger específico do teu módulo
        "src.core.control_id_monitor.infra.control_id_monitor_django_app": {
            "handlers": ["console"],
            "level": "DEBUG",  # ou INFO se não quiser tanto detalhe
            "propagate": False,
        },
    },
}

MINIO_STORAGE_ENDPOINT = os.getenv(
    "MINIO_STORAGE_ENDPOINT", "minio.fabricadesoftware.ifc.edu.br"
)
MINIO_STORAGE_ACCESS_KEY = os.getenv("MINIO_STORAGE_ACCESS_KEY", "my_access_key")
MINIO_STORAGE_SECRET_KEY = os.getenv("MINIO_STORAGE_SECRET_KEY", "my_secret_key")
MINIO_STORAGE_USE_HTTPS = os.getenv("MINIO_STORAGE_USE_HTTPS", "True") == "True"
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "minio.fabricadesoftware.ifc.edu.br")

# Configurar o Minio como armazenamento padrão
DEFAULT_FILE_STORAGE = "minio_storage.storage.MinioMediaStorage"
STATICFILES_STORAGE = "minio_storage.storage.MinioStaticStorage"

# Nome do bucket e criação automática
MINIO_STORAGE_MEDIA_BUCKET_NAME = "catraca"
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True

BIOMETRIC_DEVICE_API_KEY = os.getenv(
    "BIOMETRIC_DEVICE_API_KEY",
    "troque-esta-chave-do-dispositivo",
)
