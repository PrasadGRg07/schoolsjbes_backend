from django.db import models


class SchoolInfo(models.Model):
    """Singleton model for core school information."""
    name = models.CharField(max_length=200, default='Shree Jaya Buddha English Boarding School')
    short_name = models.CharField(max_length=20, default='SJBEBS')
    tagline = models.CharField(max_length=300, blank=True)
    logo = models.ImageField(upload_to='school/', blank=True, null=True)
    logo_url = models.URLField(blank=True)  # Cloudinary URL
    hero_image_url = models.URLField(
        blank=True,
        default='https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=1600&auto=format&fit=crop'
    )
    established_year = models.PositiveIntegerField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nepal')
    phone_primary = models.CharField(max_length=20, blank=True)
    phone_secondary = models.CharField(max_length=20, blank=True)
    email_primary = models.EmailField(blank=True)
    email_secondary = models.EmailField(blank=True)
    map_embed_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'School Information'
        verbose_name_plural = 'School Information'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce singleton
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
