from django.core.management.base import BaseCommand
from accounts.models import AdminUser

class Command(BaseCommand):
    help = 'Creates a temporary superuser'

    def handle(self, *args, **options):
        if not AdminUser.objects.filter(username='admin').exists():
            AdminUser.objects.create_superuser('admin', 'admin@example.com', 'password')
            self.stdout.write(self.style.SUCCESS('Successfully created temporary superuser'))
        else:
            self.stdout.write(self.style.WARNING('Temporary superuser already exists'))
