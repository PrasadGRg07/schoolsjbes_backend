from django.db import models


class NewsEvent(models.Model):
    TYPE_CHOICES = [
        ('news', 'News'),
        ('event', 'Event'),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=350, unique=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='news')
    content = models.TextField()
    excerpt = models.TextField(blank=True, max_length=400)
    cover_image_url = models.URLField(blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_location = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'News / Event'
        verbose_name_plural = 'News & Events'

    def __str__(self):
        return self.title
