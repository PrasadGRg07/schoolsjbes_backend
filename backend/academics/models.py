from django.db import models
from django.db.models import Q

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


class Chapter(models.Model):
    """
    A chapter of a subject, e.g. "Chapter 1 - Real Numbers" under Grade 10
    Mathematics.

    This sits between the subject and the document so a file can be filed under
    the chapter it belongs to instead of loose on the subject. Two chapters of
    one subject cannot share a name, because the document form looks them up by
    name as well as by id.
    """

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['subject', 'name'], name='uniq_chapter_per_subject'),
        ]

    def __str__(self):
        return f"{self.subject.name} — {self.name}"


class AcademicDocument(models.Model):
    """
    A piece of learning material, filed as programme → subject → chapter.

    `programme` alone used to be the only way to place a document, so notes for
    different chapters of the same subject had nothing to tell them apart. The
    subject and chapter narrow where the material belongs, and `document_type`
    says what kind of thing it is.
    """

    DOCUMENT_TYPES = [
        ('study_material', 'Chapter / Study Material'),
        ('pdf_notes', 'PDF / Notes'),
        ('questions', 'Questions'),
        ('qa', 'Questions & Answers'),
        ('assignment', 'Assignment'),
        ('pyq', 'Previous Year Questions'),
        ('other', 'Other'),
    ]

    STATUS = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    #: The types that hold questions rather than a file to open.
    QUESTION_TYPES = ('questions', 'qa')

    title = models.CharField(max_length=200)
    # Blank for a questions-only document, which has nothing to download. The
    # serializer still requires a file for every other type.
    file_url = models.URLField(blank=True)
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    chapter = models.ForeignKey(Chapter, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='study_material')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    # A value the form makes once and resends on every save. A double-clicked
    # Save sends it twice, which the serializer turns back into one document.
    client_token = models.CharField(max_length=64, blank=True, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        constraints = [
            # Only tokens that were actually sent take part, so documents saved
            # by anything that does not send one are unaffected.
            models.UniqueConstraint(
                fields=['client_token'],
                condition=~Q(client_token=''),
                name='uniq_document_client_token',
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def holds_questions(self):
        return self.document_type in self.QUESTION_TYPES


class DocumentQuestion(models.Model):
    """One question inside a document of type Questions or Questions & Answers."""

    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('short_answer', 'Short Answer'),
        ('long_answer', 'Long Answer'),
        ('true_false', 'True / False'),
    ]

    document = models.ForeignKey(AcademicDocument, on_delete=models.CASCADE, related_name='questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='short_answer')
    # Option A-D for a multiple choice question, stored the way Subject.images
    # and Programme.images are: a list on the row, because nothing is ever
    # queried by anything except its position.
    options = models.JSONField(default=list, blank=True)
    # The letter of the right option, as shown to the student. Blank for the
    # question types that have no options to pick from.
    correct_option = models.CharField(max_length=1, blank=True)
    answer = models.TextField(blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.question[:60]


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

    @property
    def class_teacher(self):
        """
        The single teacher in charge of this class, or None.

        The relationship really lives on ClassTeacher, so this reads it instead
        of storing it twice. It exists because the API has to report the chosen
        teacher as a value the admin form can compare against - without it the
        dropdown has nothing to match and springs back to blank.
        """
        rows = getattr(self, '_prefetched_assignments', None)
        if rows is None:
            rows = self.teacher_assignments.filter(is_active=True).select_related('teacher')
        for row in rows:
            if row.is_class_teacher:
                return row.teacher
        return None


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
        (6, 'Sunday'),
    ]

    teacher = models.ForeignKey(
        'accounts.AdminUser',
        on_delete=models.CASCADE,
        related_name='teaching_slots',
        limit_choices_to={'role': 'teacher'},
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='teaching_slots')
    # A real link to the subject list, so the timetable, the results marks and
    # the subjects page all name the same thing. PROTECT rather than CASCADE:
    # deleting a subject that is on the timetable is refused with a clear message
    # instead of quietly taking the periods with it.
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='timetable_slots')
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


class Student(models.Model):
    """
    A pupil enrolled in a class.

    Results used to know a student only as typed-in name and roll number, which
    meant the same child could be spelled two ways and no one could look up
    their history. This is the roster that attendance and marks both hang off.
    """

    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='students')
    name = models.CharField(max_length=200)
    roll_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['school_class__name', 'roll_number', 'name']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        constraints = [
            # A roll number identifies one child within a class. Blank roll
            # numbers are left free, because plenty of classes have them and two
            # blanks in the same class are not the same child.
            models.UniqueConstraint(
                fields=['school_class', 'roll_number'],
                condition=~Q(roll_number=''),
                name='uniq_student_roll_per_class',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.school_class})'


class Attendance(models.Model):
    """
    Whether a student was in school on one date.

    One row per student per day, so the timetable calendar can simply ask which
    dates have attendance and colour them. Taking it per period would be more
    precise but needs a second key; that can be added without losing these rows.
    """

    STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS, default='present')
    note = models.CharField(max_length=200, blank=True)
    marked_by = models.ForeignKey(
        'accounts.AdminUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attendance_marked',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'student__roll_number', 'student__name']
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance'
        constraints = [
            # Marking the same student twice in a day updates the row instead
            # of piling up duplicates that would double-count the register.
            models.UniqueConstraint(fields=['student', 'date'], name='uniq_attendance_student_date'),
        ]

    def __str__(self):
        return f'{self.student} on {self.date}: {self.get_status_display()}'
