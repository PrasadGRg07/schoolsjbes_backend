from django.db import models


class TextSlide(models.Model):
    """Configurable text banner/slide for the homepage text carousel."""
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    button_text = models.CharField(max_length=100, blank=True)
    button_url = models.CharField(max_length=500, blank=True)
    is_enabled = models.BooleanField(default=True, help_text="Show this slide on the homepage.")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class ImageSlide(models.Model):
    """Configurable image slide for the homepage image carousel."""
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    image_url = models.URLField(blank=True, help_text="Direct image URL or Cloudinary URL.")
    image = models.ImageField(upload_to='carousel/', blank=True, null=True)
    link_url = models.CharField(max_length=500, blank=True)
    is_enabled = models.BooleanField(default=True, help_text="Show this slide on the homepage.")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title or f'Image slide {self.pk}'

    def resolved_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url
