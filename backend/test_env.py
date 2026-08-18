import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()
from django.conf import settings
print("DEBUG:", getattr(settings, 'DEBUG', False))
key = getattr(settings, 'CLOUDINARY_STORAGE', {}).get('API_KEY', '')
print("API_KEY:", repr(key))
print("not key:", not key)
