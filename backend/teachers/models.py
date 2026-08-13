from django.db import models


class Teacher(models.Model):
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    subject = models.CharField(max_length=200, blank=True)
    qualification = models.CharField(max_length=300, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Teacher'

    def __str__(self):
        return f"{self.name} — {self.designation}"
