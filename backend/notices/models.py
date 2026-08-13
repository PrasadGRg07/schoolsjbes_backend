from django.db import models


class Notice(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('exam', 'Exam'),
        ('holiday', 'Holiday'),
        ('admission', 'Admission'),
        ('result', 'Result'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    description = models.TextField(blank=True)
    file_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    is_important = models.BooleanField(default=False)
    published_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_important', '-published_date']

    def __str__(self):
        return self.title
