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


class SchoolClass(models.Model):
    """
    A class group such as "Grade 7" or "Nursery A".

    This exists so a teacher can be given charge of a class and then only see
    and edit the students in it. The free-text `class_name` on Exam is kept for
    display, and `Exam.school_class` is the reliable link used for scoping.
    """

    name = models.CharField(max_length=100, unique=True)
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.name


class ClassTeacher(models.Model):
    """
    Links a teacher to a class they teach in.

    A teacher may teach in several classes, and a class may have several
    teachers. Exactly one of them can be flagged as the *class teacher* - the
    person in charge of the class - which the constraint below enforces at the
    database level rather than trusting the interface.
    """

    teacher = models.ForeignKey(
        'accounts.AdminUser',
        on_delete=models.CASCADE,
        related_name='class_assignments',
        limit_choices_to={'role': 'teacher'},
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='teacher_assignments')
    # True only for the single teacher in charge of the class.
    is_class_teacher = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['school_class__order', 'school_class__name']
        constraints = [
            models.UniqueConstraint(fields=['teacher', 'school_class'], name='uniq_teacher_class'),
            # One class teacher per class. The condition keeps this as a partial
            # index, so several non-class teachers can share the same class.
            models.UniqueConstraint(
                fields=['school_class'],
                condition=models.Q(is_class_teacher=True, is_active=True),
                name='uniq_class_teacher_per_class',
            ),
        ]

    def __str__(self):
        role = 'class teacher' if self.is_class_teacher else 'teacher'
        return f"{self.teacher} as {role} of {self.school_class}"


class Exam(models.Model):
    """
    One result session: a class, a term and an academic year, optionally scoped
    to a programme. The published result sheet is attached here, so a school can
    publish a downloadable result file for the whole class without creating a
    row per student just to hold a PDF.
    """

    title = models.CharField(max_length=200)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, null=True, blank=True, related_name='exams')
    # The class this session belongs to. Null until an admin links it, so an
    # existing sheet entered with only a class name still works.
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams',
    )
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



class TeachingSlot(models.Model):
    """
    One period on the timetable: a teacher teaching a subject to a class on a
    given weekday between two times.

    Kept separate from the class assignment on purpose: a teacher being in
    charge of Grade 7 says nothing about *when* they teach it, and one teacher
    often covers several subjects in the same class.
    """

    DAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
    ]

    teacher = models.ForeignKey(
        'accounts.AdminUser',
        on_delete=models.CASCADE,
        related_name='teaching_slots',
        limit_choices_to={'role': 'teacher'},
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='teaching_slots')
    # Free text rather than a foreign key, so a teacher can be timetabled for a
    # subject that is taught but has not been added to the subjects list yet.
    subject = models.CharField(max_length=200)
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'start_time', 'school_class__name']
        verbose_name = 'Teaching slot'
        verbose_name_plural = 'Teaching slots'
        constraints = [
            # Two periods cannot start together for the same teacher and class.
            models.UniqueConstraint(
                fields=['teacher', 'school_class', 'day_of_week', 'start_time'],
                name='uniq_teacher_slot_start',
            ),
        ]

    def __str__(self):
        day = dict(self.DAYS).get(self.day_of_week, '?')
        return f"{self.teacher} — {self.subject} — {day} {self.start_time:%H:%M}"
