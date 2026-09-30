from django.db import models

from config.models import CoverCropMixin


class NewsEvent(CoverCropMixin, models.Model):
    TYPE_CHOICES = [
        ('news', 'News'),
        ('event', 'Event'),
    ]

    # Title and excerpt are rich text, so they hold allowlisted HTML. The caps
    # below are on the stored markup; the visible text is capped separately in
    # the serializer, because ~300 characters of formatted text is far more
    # markup than 300 characters of plain text.
    title = models.CharField(max_length=1500)
    slug = models.SlugField(max_length=350, unique=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='news')
    content = models.TextField()
    excerpt = models.TextField(blank=True, max_length=2500)
    cover_image_url = models.URLField(blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_location = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=True)
    show_popup = models.BooleanField(default=False)
    popup_expires_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'News / Event'
        verbose_name_plural = 'News & Events'

    def __str__(self):
        return self.title
