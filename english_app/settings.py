from pathlib import Path
from datetime import timedelta

import os
import environ


BASE_DIR = Path(__file__).resolve().parent.parent

# ====================
# Basic Configurations
# ====================
INSTALLED_APPS = [
    # default django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third-party apps
    "corsheaders",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "storages",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",

    # custom apps
    "accounts",
]

MIDDLEWARE = [
    # default django middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # third-party middleware
    "corsheaders.middleware.CorsMiddleware",
]

ROOT_URLCONF = "english_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "english_app.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Ho_Chi_Minh"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=3000),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "English App API",
    "DESCRIPTION": "API documentation",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY_SCHEMES": {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "BasicAuth": {
            "type": "http",
            "scheme": "basic",
        },
    },
    "SECURITY": [{"BearerAuth": []}, {"BasicAuth": []}],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

# ====================
# Enviroment Variables
# ====================
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# general
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# database
DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE"),
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
}

# cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{env('REDIS_HOST')}:{env('REDIS_PORT')}/{env('REDIS_DB')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# email
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_BACKEND = env("EMAIL_BACKEND")

# oauth2
OAUTH2_GOOGLE_KEY = env("OAUTH2_GOOGLE_KEY")
OAUTH2_GOOGLE_SECRET = env("OAUTH2_GOOGLE_SECRET")
OAUTH2_GOOGLE_SCOPE = env("OAUTH2_GOOGLE_SCOPE")

OAUTH2_FACEBOOK_KEY = env("OAUTH2_FACEBOOK_KEY")
OAUTH2_FACEBOOK_SECRET = env("OAUTH2_FACEBOOK_SECRET")
OAUTH2_FACEBOOK_SCOPE = env("OAUTH2_FACEBOOK_SCOPE")

# gcs
GCS_PUBLIC_BASE_URL = env("GCS_PUBLIC_BASE_URL")
GCS_PROJECT_ID = env("GCS_PROJECT_ID")

# dev vs prod
if DEBUG:
    OAUTH2_GOOGLE_REDIRECT_URI = env("OAUTH2_GOOGLE_DEV_REDIRECT_URI")
    OAUTH2_FACEBOOK_REDIRECT_URI = env("OAUTH2_FACEBOOK_DEV_REDIRECT_URI")
    GCS_BUCKET_NAME = env("GCS_DEV_BUCKET")
    CORS_ALLOW_ALL_ORIGINS = env.bool("DEV_CORS_ALLOW_ALL_ORIGINS")
    CORS_ALLOWED_ORIGINS = []
else:
    OAUTH2_GOOGLE_REDIRECT_URI = env("OAUTH2_GOOGLE_PRODUCTION_REDIRECT_URI")
    OAUTH2_FACEBOOK_REDIRECT_URI = env("OAUTH2_FACEBOOK_PRODUCTION_REDIRECT_URI")
    GCS_BUCKET_NAME = env("GCS_PRODUCTION_BUCKET")
    CORS_ALLOW_ALL_ORIGINS = env.bool("PRODUCTION_CORS_ALLOW_ALL_ORIGINS")
    CORS_ALLOWED_ORIGINS = env.list("PRODUCTION_CORS_ALLOWED_ORIGINS")

# storages
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GCS_BUCKET_NAME,
            "project_id": GCS_PROJECT_ID,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = f"{GCS_PUBLIC_BASE_URL}/{GCS_BUCKET_NAME}/"
