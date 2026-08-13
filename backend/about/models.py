from django.db import models


class PrincipalMessage(models.Model):
    """Singleton — Principal's message on the About page."""
    principal_name = models.CharField(max_length=200)
    principal_title = models.CharField(max_length=200, default='Principal')
    photo_url = models.URLField(blank=True)
    message = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Principal's Message"

    def __str__(self):
        return f"Principal: {self.principal_name}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class SchoolHistory(models.Model):
    """About page — school history, mission, vision."""
    history = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    values = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'School History'

    def __str__(self):
        return 'School History & Mission'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
