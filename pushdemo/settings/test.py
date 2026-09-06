from .base import *  # noqa: F403,F401

DEBUG = True

# Test sunucusu icin sabit ayarlar. Bu surum .env / env_file kullanmaz.
SECRET_KEY = "O_5FzZySfgFderPM2uRaVTr9sQyPFJuzpjOBHD1hXxqnI3Fjp8VdQ7SwVaLr4bBQCSJ4adHx94rsIpmss_ZyNQ"

ALLOWED_HOSTS = [
    "testplatform.farmingo.com.tr",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://testplatform.farmingo.com.tr",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "pushdemo",
        "USER": "pushdemo",
        "PASSWORD": "as9EoNGjvMlVGYUjlAlWVagIDQtPQIou4nboZMCHLnc",
        "HOST": "db",
        "PORT": "5432",
        "CONN_MAX_AGE": 60,
    }
}

VAPID_SUBJECT = "https://testplatform.farmingo.com.tr"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo12345!"
DEMO_EMAIL = "demo@example.com"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Host Nginx static dosyalari uzun sure cache'leyebilir. Hash'li dosya adlari
# kullanarak yeni deploy'da eski JS'in tutulmasini onler.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}
