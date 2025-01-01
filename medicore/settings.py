from pathlib import Path
import environ
from datetime import timedelta

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

# Application definition
# List of default Django apps and third-party apps that are common to both shared and tenant apps
DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "rest_framework_simplejwt",
    "corsheaders",
]

# Apps that are specific to individual tenants
TENANT_APPS = [
    *DEFAULT_APPS,  # Unpack default apps
    "apps.patients",  # Example tenant-specific app
    "apps.staff",
    # "apps.doctors",
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
    "corsheaders.middleware.CorsMiddleware",
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.AdminAccessMiddleware",
    "core.middleware.JWTRefreshMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "medicore.middleware.DynamicAuthModelMiddleware",
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
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)


# CACHES = {
#     "default": {
#         'KEY_FUNCTION': 'django_tenants.cache.make_key',
#         'REVERSE_KEY_FUNCTION': 'django_tenants.cache.reverse_key',
#     },
# }

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
        "core.authentication.RobustCookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.patients.permissions.RolePermission",
    ],
}


JWT_AUTH_COOKIE = "access_token"
JWT_AUTH_REFRESH_COOKIE = "refresh_token"
JWT_AUTH_SECURE = False
JWT_AUTH_SAMESITE = "Lax"
JWT_AUTH_HTTPONLY = True

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_COOKIE": JWT_AUTH_COOKIE,
    "AUTH_COOKIE_REFRESH": JWT_AUTH_REFRESH_COOKIE,
}
# Tenant vs Public Schema User Model Configuration
PUBLIC_SCHEMA_USER_MODEL = "core.MyUser"
TENANT_SCHEMA_USER_MODEL = "staff.StaffMember"


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
    "core.backends.MultiSchemaModelBackend",
    "django.contrib.auth.backends.ModelBackend",
)

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

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

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Add your frontend URL here
    "http://city-hospital.medicore.local",
]

CORS_ALLOW_CREDENTIALS = True

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
