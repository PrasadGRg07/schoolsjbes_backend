from django.db import models


class Teacher(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    qualification = models.CharField(max_length=300, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    gender = models.CharField(max_length=20, blank=True, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'

    def __str__(self):
        return f"{self.name} — {self.designation}"
