from django.db import models


class SiteSettings(models.Model):
    """Singleton — Global site configuration."""
    maintenance_mode = models.BooleanField(default=False)
    meta_title = models.CharField(max_length=200, default='SJBEBS — Shree Jaya Buddha English Boarding School')
    meta_description = models.TextField(blank=True, default='Official website of Shree Jaya Buddha English Boarding School.')
    meta_keywords = models.TextField(blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    main_background_image = models.ImageField(upload_to='backgrounds/', blank=True, null=True, help_text="Background image for the main website.")
    admin_background_image = models.ImageField(upload_to='backgrounds/', blank=True, null=True, help_text="Background image for the admin dashboard.")
    footer_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
