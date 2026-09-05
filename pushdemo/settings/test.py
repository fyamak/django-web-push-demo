from .base import *  # noqa: F403,F401

DEBUG = False
SECRET_KEY = "django-web-push-demo-test-secret-key-change-before-real-use"
ALLOWED_HOSTS = ["31.97.37.175", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["https://31.97.37.175", "http://31.97.37.175"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "pushdemo",
        "USER": "pushdemo",
        "PASSWORD": "pushdemo-test-password",
        "HOST": "db",
        "PORT": "5432",
        "CONN_MAX_AGE": 60,
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
