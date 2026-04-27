from .base import *  # noqa: F401,F403

DEBUG = False
ROOT_URLCONF = "src.django_project.urls"
INSTALLED_APPS = [
    app for app in INSTALLED_APPS if app not in {"minio_storage", "debug_toolbar"}
]
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE
    if middleware != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_catraca.sqlite3",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
USE_MINIO_STORAGE = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = False

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
AXES_ENABLED = False


class DisableMigrations(dict):
    def __contains__(self, app_label):
        return True

    def __getitem__(self, app_label):
        return None

    def get(self, app_label, default=None):
        return None


MIGRATION_MODULES = DisableMigrations()

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
