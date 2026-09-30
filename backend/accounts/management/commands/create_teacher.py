from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AdminUser
from academics.models import ClassTeacher, SchoolClass


class Command(BaseCommand):
    help = 'Creates or updates a teacher login account and assigns it classes'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--password', required=True, help='Password for the account')
        parser.add_argument('--email', default='')
        parser.add_argument('--first-name', default='')
        parser.add_argument('--last-name', default='')
        parser.add_argument(
            '--classes',
            default='',
            help='Comma separated class names. Classes are created if they do not exist.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username']

        # A teacher is deliberately not staff: that flag is what the write
        # permission checks, and it is also what the Django admin login uses.
        teacher, created = AdminUser.objects.get_or_create(
            username=username,
            defaults={
                'email': options['email'],
                'first_name': options['first_name'],
                'last_name': options['last_name'],
            },
        )
        teacher.role = AdminUser.ROLE_TEACHER
        teacher.is_staff = False
        teacher.is_superuser = False
        if options['email']:
            teacher.email = options['email']
        if options['first_name']:
            teacher.first_name = options['first_name']
        if options['last_name']:
            teacher.last_name = options['last_name']
        teacher.set_password(options['password'])
        teacher.save()

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} teacher account "{username}"'))

        names = [n.strip() for n in options['classes'].split(',') if n.strip()]
        for name in names:
            school_class, _ = SchoolClass.objects.get_or_create(name=name)
            _, link_created = ClassTeacher.objects.get_or_create(
                teacher=teacher,
                school_class=school_class,
            )
            suffix = 'assigned' if link_created else 'already assigned to'
            self.stdout.write(f'  Class {name} {suffix} {username}')

        if not names:
            self.stdout.write(
                self.style.WARNING(
                    '  No classes assigned, so this teacher will see an empty dashboard.'
                )
            )
