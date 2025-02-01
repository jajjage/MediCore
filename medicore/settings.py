from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure$@")
ENCRYPTION_KEY = env("ENCRYPTION_KEY", default="")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG", default=True)

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="*").split(",")
BASE_URL = env("BASE_URL", default="http://.medicore.local:8000/api/v1/")
# Application definition
# List of default Django apps and third-party apps that are common to both shared and tenant apps
DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "rest_framework_simplejwt",
    "corsheaders",
    "simple_history",
    "django_filters",
]

# Apps that are specific to individual tenants
TENANT_APPS = [
    "apps.patients",  # Example tenant-specific app
    "apps.staff",
    "apps.scheduling",
    # "apps.nurses",
    # "apps.receptionists",
]

# Apps that are shared across all tenants
SHARED_APPS = [
    *DEFAULT_APPS,  # Unpack default apps
    "django_tenants",
    "tenants",
    "core",
    "hospital",
]

# Validate that all tenant apps are also in INSTALLED_APPS
INSTALLED_APPS = list(set(SHARED_APPS) | set(TENANT_APPS))

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "medicore.middleware.SubdomainTenantMiddleware",

]

ROOT_URLCONF = "medicore.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "medicore.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",  # Changed from django_tenant_schemas.postgresql_backend
        "NAME": env("POSTGRES_DB", default="medicore_db"),
        "USER": env("POSTGRES_USER", default="medicore_user"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="medicore_password"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)


# settings.py

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",  # Redis URL
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "medicore",  # Optional, helps avoid key collisions
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "REVERSE_KEY_FUNCTION": "django_tenants.cache.reverse_key",
    }
}

CACHE_TIMEOUTS = {
    "PATIENT_SEARCH": 3600,  # 1 hour
    "PATIENT_DETAIL": 86400,  # 24 hours
}

CACHE_KEYS = {
    "PATIENT_SEARCH": "patient_search:{query}",
    "PATIENT_DETAIL": "patient_detail:{id}",
}
# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

BASE_DOMAIN = "medicore.local"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "medicore.authentication.RobustCookieJWTAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}


JWT_AUTH_COOKIE = "access_token"
JWT_AUTH_REFRESH_COOKIE = "refresh_token"
JWT_REFRESH_THRESHOLD = 300  # 5 minutes in seconds
JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
JWT_REFRESH_TOKEN_LIFETIME = timedelta(days=1)
JWT_AUTH_SECURE = False
JWT_AUTH_SAMESITE = "Lax"
JWT_AUTH_HTTPONLY = True
JWT_AUTH_PATH = "/"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": JWT_ACCESS_TOKEN_LIFETIME,
    "REFRESH_TOKEN_LIFETIME": JWT_REFRESH_TOKEN_LIFETIME,
    "TOKEN_OBTAIN_SERIALIZER": "core.serializers.CustomTokenObtainSerializer",
    "AUTH_COOKIE": JWT_AUTH_COOKIE,
    "AUTH_COOKIE_REFRESH": JWT_AUTH_REFRESH_COOKIE,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}


# Add API settings
API_VERSION = "v1"
API_BASE_PATH = f"/api/{API_VERSION}"
SITE_DOMAIN = "medicore.local"
SITE_SCHEME = "http" if DEBUG else "https"
API_TIMEOUT = 5
API_MAX_RETRIES = 3
LOCAL_PORT = 8000 if DEBUG else 80
# JWT settings
JWT_AUTH_ENDPOINTS = {
    "refresh": f"{API_BASE_PATH}/auth/token/refresh/",
    "verify": f"{API_BASE_PATH}/auth/token/verify/",
    "obtain": f"{API_BASE_PATH}/auth/token/",
}

DJOSER = {
    "LOGIN_FIELD": "email",
    "SERIALIZERS": {
        "user_create": "apps.staff.serializers.TenantStaffCreateSerializer",
        "user": "apps.staff.serializers.StaffSerializer",
        "current_user": "apps.staff.serializers.StaffSerializer",
    },
}


# Custom authentication backend
AUTHENTICATION_BACKENDS = (
    "medicore.backends.TenantAuthBackend",
)

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
# STATIC_ROOT = str(BASE_DIR / "staticfiles")
# STATICFILES_DIRS = [
#     str(BASE_DIR / "static"),
# ]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.MyUser"


TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_NAME = "public"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "debug.log",
        },
    },
    "loggers": {
        "core.authentication": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

CORS_ALLOWED_ORIGINS = str(env("CORS_ALLOWED_ORIGINS", default="*")).split(",")
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE", default=True)
CSRF_TRUSTED_ORIGINS = ["http://*", "https://*"]
ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS.copy()

# Ensure cookies are allowed
CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "x-csrftoken",
    "x-requested-with",
    "accept",
    "origin",
    "access-control-allow-origin",
    "access-control-allow-credentials",
]

# Ensure cookies are allowed in responses
CORS_EXPOSE_HEADERS = [
    "Set-Cookie",
]

# settings.py
# settings.py
CELERY_BROKER_URL = "redis://redis:6379/1"  # ← Change from localhost to redis
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
CELERY_TIMEZONE = "UTC"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"


CELERY_BEAT_SCHEDULE = {
    "generate-shifts-every-day": {
        "task": "apps.scheduling.tasks.generate_shifts",
        "schedule": crontab(hour=2, minute=30),  # 2:30 AM daily
    },
}
