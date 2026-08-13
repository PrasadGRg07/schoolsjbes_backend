from django.db import models


class AdmissionInfo(models.Model):
    """Singleton — General admission information displayed on the page."""
    intro = models.TextField(blank=True)
    eligibility = models.TextField(blank=True)
    process = models.TextField(blank=True)
    required_documents = models.TextField(blank=True)
    fee_structure = models.TextField(blank=True)
    open_for_admission = models.BooleanField(default=True)
    academic_year = models.CharField(max_length=20, blank=True)
    deadline = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Admission Information'

    def __str__(self):
        return 'Admission Information'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class AdmissionApplication(models.Model):
    """Online admission form submissions."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    student_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    grade_applying = models.CharField(max_length=50)
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)
    parent_email = models.EmailField(blank=True)
    address = models.TextField()
    previous_school = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student_name} — Grade {self.grade_applying}"
