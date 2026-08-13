from django.db import models


class Programme(models.Model):
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=100, blank=True)
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
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.programme.name} — {self.name}"


class AcademicDocument(models.Model):
    title = models.CharField(max_length=200)
    file_url = models.URLField()
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
