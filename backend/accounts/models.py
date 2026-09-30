from django.db import models
from django.contrib.auth.models import AbstractUser


class AdminUser(AbstractUser):
    """
    Every person who can sign in to the back office: administrators and teachers.

    Despite the historical name this is the project's single user model. The
    `role` decides which sign-in page a person belongs to and what they may
    write, so an account created as a teacher can never reach admin tooling.
    """

    ROLE_ADMIN = 'admin'
    ROLE_TEACHER = 'teacher'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_TEACHER, 'Teacher'),
    ]

    # Existing rows are administrators: every account predates teachers and
    # belongs to whoever runs the site.
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_ADMIN, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    # Optional link to the public staff profile shown on the Teachers page.
    teacher_profile = models.OneToOneField(
        'teachers.Teacher',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_account',
    )

    class Meta:
        verbose_name = 'Admin User'
        verbose_name_plural = 'Admin Users'

    def __str__(self):
        return self.username

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    @property
    def display_name(self):
        """A friendly name to show in a dashboard greeting."""
        full = self.get_full_name().strip()
        return full or self.username
