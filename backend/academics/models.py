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


class Exam(models.Model):
    """
    One result session: a class, a term and an academic year, optionally scoped
    to a programme. The published result sheet is attached here, so a school can
    publish a downloadable result file for the whole class without creating a
    row per student just to hold a PDF.
    """

    title = models.CharField(max_length=200)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, null=True, blank=True, related_name='exams')
    class_name = models.CharField(max_length=100, blank=True)
    term = models.CharField(max_length=100, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)
    # The downloadable result sheet for the whole class, if there is one.
    result_file_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-academic_year', '-created_at']

    def __str__(self):
        return self.title

    @property
    def total_students(self):
        return self.results.count()


class StudentResult(models.Model):
    """
    A student's overall result in one exam. The per-subject breakdown hangs off
    this row, and the totals are stored as well as summed so an entered overall
    score is never silently overwritten by its parts.
    """

    GRADE_CHOICES = [
        ('A+', 'A+'), ('A', 'A'), ('B+', 'B+'), ('B', 'B'),
        ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student_name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, blank=True)
    # Overall score, entered directly or derived from the subject marks.
    total_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    remark = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'student_name']
        # One row per student per exam, so a student cannot be listed twice.
        constraints = [
            models.UniqueConstraint(fields=['exam', 'student_name'], name='unique_student_per_exam'),
        ]

    def __str__(self):
        return f"{self.student_name} — {self.exam.title}"

    @property
    def percentage(self):
        if not self.total_score or not self.max_score:
            return None
        return round(float(self.total_score) / float(self.max_score) * 100, 2)

    def sync_totals(self):
        """
        Fill the overall score from the subject marks, but only when the author
        has not already typed one of their own.
        """
        if self.total_score is not None:
            return
        marks = list(self.marks.all())
        if not marks:
            return
        self.total_score = sum(m.marks_obtained for m in marks)
        self.max_score = sum(m.max_marks for m in marks)


class SubjectMark(models.Model):
    """One subject's mark for one student in one exam."""

    result = models.ForeignKey(StudentResult, on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='marks')
    # Kept as text so a mark can be "85", "A" or "Absent" without a schema change.
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    subject_name = models.CharField(max_length=200, blank=True)
    remark = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.result.student_name} — {self.name}"

    @property
    def name(self):
        return self.subject.name if self.subject_id else (self.subject_name or "Subject")

