from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# WhiteNoise for static files
# (WhiteNoise middleware is already added in base.py)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
