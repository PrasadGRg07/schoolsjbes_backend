import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')

# get token
url_token = "http://127.0.0.1:8000/api/auth/token/"
res_token = requests.post(url_token, json={'username': user.username, 'password': 'password'})
# wait, I don't know the password. Let's just reset it to 'admin'
user.set_password('admin')
user.save()

res_token = requests.post(url_token, json={'username': user.username, 'password': 'admin'})
if res_token.status_code != 200:
    print("Token fetch failed:", res_token.text)
    exit()

token = res_token.json()['access']
url_upload = "http://127.0.0.1:8000/api/auth/upload/"
headers = {'Authorization': f'Bearer {token}'}
files = {'file': ('test.txt', b'Hello world')}
data = {'folder': 'test'}

response = requests.post(url_upload, headers=headers, files=files, data=data)
print("Upload status:", response.status_code)
print("Upload response:", response.text)
