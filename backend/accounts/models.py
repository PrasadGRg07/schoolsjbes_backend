from django.db import models
from django.contrib.auth.models import AbstractUser


class AdminUser(AbstractUser):
    """Single admin user for the school website."""
    phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name = 'Admin User'
        verbose_name_plural = 'Admin Users'

    def __str__(self):
        return self.username
