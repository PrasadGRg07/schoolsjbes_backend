from django.db import models

from config.models import CoverCropMixin


class Programme(CoverCropMixin, models.Model):
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=100, blank=True)
    cover_image_url = models.URLField(blank=True)
    images = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Subject(models.Model):
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    # Short summary for listings, plus the full write-up shown on the subject's
    # own page. Both are rich text, sanitised in the serializer.
    description = models.TextField(blank=True)
    profile = models.TextField(blank=True)
    # Image URLs, matching how Programme.images is stored. A separate table was
    # not needed: nothing is queried by anything but position.
    images = models.JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.programme.name} — {self.name}"


class SubjectFile(models.Model):
    """A downloadable file on a subject — notes, syllabus, past paper."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='files')
    title = models.CharField(max_length=200)
    file_url = models.URLField()
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-uploaded_at']

    def __str__(self):
        return f"{self.subject.name} — {self.title}"


class AcademicDocument(models.Model):
    title = models.CharField(max_length=200)
    file_url = models.URLField()
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
