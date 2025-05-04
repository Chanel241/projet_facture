from .settings import *
from decouple import config

# Database configuration for production (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        },
    },
}

# Disable debug mode in production
DEBUG = False

# Trusted origins for CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://chaneltest.blog',
    'http://chaneltest.blog',
    'http://127.0.0.1',
    'http://localhost',
]

# Uncomment if using subdomains
# CSRF_COOKIE_DOMAIN = '.chaneltest.blog'

# Additional security settings
SECURE_HSTS_SECONDS = 31536000  # Enable HSTS for 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
CSP_DEFAULT_SRC = ("'self'",)