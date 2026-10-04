from django.db.models import Q
from rest_framework import serializers
from config.html import sanitize_html
from .models import (
    Programme, Subject, SubjectFile, Chapter, AcademicDocument, DocumentQuestion,
    Exam, StudentResult, SubjectMark, SchoolClass, ClassTeacher, TeachingSlot,
    Student, Attendance,
)
from accounts.models import AdminUser


class SubjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectFile
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    """Full subject, including its files — used for the admin form and detail."""

    files = SubjectFileSerializer(many=True, read_only=True)
    file_count = serializers.IntegerField(source='files.count', read_only=True)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=None,
        style={'base_template': 'textarea.html'},
    )
    profile = serializers.CharField(
        required=False, allow_blank=True, max_length=None,
        style={'base_template': 'textarea.html'},
    )

    class Meta:
        model = Subject
        fields = '__all__'

    def validate_description(self, value):
        return sanitize_html(value or '')

    def validate_profile(self, value):
        return sanitize_html(value or '')


class SubjectListSerializer(serializers.ModelSerializer):
    """Subject summary for a programme's page, so cards need no second request."""

    file_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id', 'programme', 'name', 'code', 'description', 'images',
            'order', 'is_active', 'file_count',
        ]

    def get_file_count(self, obj):
        return obj.files.count()


class ProgrammeSerializer(serializers.ModelSerializer):
    subjects = SubjectListSerializer(many=True, read_only=True)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=None,
        style={'base_template': 'textarea.html'},
    )

    class Meta:
        model = Programme
        fields = '__all__'

    def validate_description(self, value):
        return sanitize_html(value or '')


class DocumentQuestionSerializer(serializers.ModelSerializer):
    """
    One question. Written nested inside the document that holds it, so the form
    saves a document and its questions in one request.

    Options are a fixed A-D set for a multiple choice question and nothing at all
    for the other types, so the four fields are normalised here rather than
    leaving a stale option list on a question that was retyped.
    """

    OPTION_LETTERS = ['A', 'B', 'C', 'D']

    options = serializers.JSONField(required=False)

    class Meta:
        model = DocumentQuestion
        fields = [
            'id', 'question', 'question_type', 'options', 'correct_option',
            'answer', 'marks', 'explanation', 'order',
        ]
        extra_kwargs = {
            'document': {'required': False},
            'question': {'required': True},
            'question_type': {'required': False},
            'answer': {'required': False, 'allow_blank': True},
            'explanation': {'required': False, 'allow_blank': True},
            'marks': {'required': False, 'allow_null': True},
            'order': {'required': False},
        }

    def validate(self, attrs):
        if not (attrs.get('question') or '').strip():
            raise serializers.ValidationError({'question': 'Type the question.'})

        question_type = attrs.get('question_type') or DocumentQuestion.QUESTION_TYPES[1][0]
        options = attrs.get('options') or []

        if question_type == 'multiple_choice':
            cleaned = [str(o).strip() for o in options][:4]
            # Short option lists are padded so the form's A-D fields always have
            # something to show, and a question cannot be saved with fewer than
            # four choices and no right answer.
            while len(cleaned) < 4:
                cleaned.append('')
            if not all(cleaned):
                raise serializers.ValidationError(
                    {'options': 'Fill in all four options, or change the question type.'}
                )
            correct = (attrs.get('correct_option') or '').strip().upper()
            if correct not in self.OPTION_LETTERS:
                raise serializers.ValidationError(
                    {'correct_option': 'Choose which option is correct.'}
                )
            attrs['options'] = cleaned
            attrs['correct_option'] = correct
        else:
            # True/False and the written types have nothing to pick between, so
            # anything left over from a retyped question is dropped.
            attrs['options'] = []
            attrs['correct_option'] = ''

        return attrs


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'subject', 'name', 'order', 'is_active', 'created_at']
        extra_kwargs = {
            'subject': {'required': True},
            'name': {'required': True},
        }


class AcademicDocumentSerializer(serializers.ModelSerializer):
    """A document, with its questions written inline alongside it."""

    questions = DocumentQuestionSerializer(many=True, required=False)
    question_count = serializers.SerializerMethodField()
    programme_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    chapter_name = serializers.SerializerMethodField()

    class Meta:
        model = AcademicDocument
        fields = [
            'id', 'title', 'file_url', 'programme', 'programme_name',
            'subject', 'subject_name', 'chapter', 'chapter_name',
            'document_type', 'description', 'status', 'client_token',
            'uploaded_at', 'updated_at', 'question_count', 'questions',
        ]
        extra_kwargs = {
            'programme': {'required': False, 'allow_null': True},
            'subject': {'required': False, 'allow_null': True},
            'chapter': {'required': False, 'allow_null': True},
            'document_type': {'required': False},
            'status': {'required': False},
            'description': {'required': False, 'allow_blank': True},
            # Sent by the form as a duplicate guard. Absent from anything that
            # does not send one, so existing callers are unaffected. The
            # uniqueness check is left to `create` below, which hands back the
            # row the first request already made instead of failing the form;
            # the database constraint still catches two truly simultaneous saves.
            'client_token': {'required': False, 'allow_blank': True, 'validators': []},
        }

    def get_question_count(self, obj):
        return obj.questions.count()

    def get_programme_name(self, obj):
        return obj.programme.name if obj.programme_id else None

    def get_subject_name(self, obj):
        return obj.subject.name if obj.subject_id else None

    def get_chapter_name(self, obj):
        return obj.chapter.name if obj.chapter_id else None

    def validate(self, attrs):
        instance = self.instance

        # A token that is already on file means this save already went through
        # and the form is being retried. Nothing is about to be written, so the
        # payload is left alone rather than judged against the rules of a first
        # save; `create` then hands back the document that exists. An update
        # carries the same token as its own stored one, so it is not skipped.
        if instance is None:
            token = attrs.get('client_token')
            if token and AcademicDocument.objects.filter(client_token=token).exists():
                return attrs

        # On an update a field that was not sent keeps its stored value, so the
        # cross-checks below have to look at the instance as well as the payload.
        def current(field, fallback=None):
            if field in attrs:
                return attrs[field]
            return getattr(instance, field, fallback) if instance else fallback

        programme = current('programme')
        subject = current('subject')
        chapter = current('chapter')
        document_type = current('document_type', AcademicDocument.DOCUMENT_TYPES[0][0])
        file_url = current('file_url', '')
        questions = attrs.get('questions')

        # The form fills these in from one another, so a mistyped or stale id is
        # caught here rather than leaving a chapter filed under the wrong subject.
        if subject and programme and subject.programme_id != programme.id:
            raise serializers.ValidationError(
                {'subject': 'That subject does not belong to the chosen programme.'}
            )
        if chapter and subject and chapter.subject_id != subject.id:
            raise serializers.ValidationError(
                {'chapter': 'That chapter does not belong to the chosen subject.'}
            )
        if chapter and not subject:
            raise serializers.ValidationError(
                {'subject': 'Choose the subject before the chapter.'}
            )

        holds_questions = document_type in AcademicDocument.QUESTION_TYPES
        # A questions document is made of its questions, and everything else is
        # a file, so each type is asked for the one thing it needs.
        if holds_questions:
            if questions is not None and not questions:
                raise serializers.ValidationError(
                    {'questions': 'Add at least one question to a questions document.'}
                )
            if questions is None and not (instance and instance.questions.exists()):
                raise serializers.ValidationError(
                    {'questions': 'Add at least one question to a questions document.'}
                )
        elif not file_url:
            raise serializers.ValidationError(
                {'file_url': 'This document type needs a file. Upload one or paste a URL.'}
            )
        return attrs

    def create(self, validated_data):
        questions = validated_data.pop('questions', [])
        token = validated_data.get('client_token')
        if token:
            # A double-clicked Save arrives as the same token twice. Handing
            # back the row the first request already made is what was meant,
            # and leaves one document rather than two.
            existing = AcademicDocument.objects.filter(client_token=token).first()
            if existing:
                return existing
        document = AcademicDocument.objects.create(**validated_data)
        self._replace_questions(document, questions)
        return document

    def _replace_questions(self, document, questions):
        """
        Write a document's questions in the order the form listed them, numbered
        from zero so the saved sequence has no gaps. The position in the list is
        the whole truth about the sequence, so an `order` sent by the client is
        dropped rather than trusted: it can go stale as soon as a question is
        removed, and keeping it would also pass `order` twice in one call.
        """
        document.questions.all().delete()
        DocumentQuestion.objects.bulk_create([
            DocumentQuestion(document=document, order=i, **{k: v for k, v in q.items() if k != 'order'})
            for i, q in enumerate(questions)
        ])

    def update(self, instance, validated_data):
        # The question list is replaced wholesale rather than merged, the same
        # way the per-subject marks are under a student result, so what is
        # saved is exactly what the form shows.
        questions = validated_data.pop('questions', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if questions is not None:
            self._replace_questions(instance, questions)
        return instance


# ── Results ──
# Three levels, each usable on its own: an Exam holds a class/term and the
# published result sheet, a StudentResult is one student's overall score, and
# SubjectMark rows are the per-subject breakdown under it.


class SubjectMarkSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SubjectMark
        fields = ['id', 'result', 'subject', 'subject_name', 'marks_obtained', 'max_marks', 'remark']
        extra_kwargs = {
            # Left optional so the same serializer works nested under a
            # StudentResult, where the parent supplies the row it belongs to.
            'result': {'required': False},
            'subject': {'required': False, 'allow_null': True},
            'marks_obtained': {'required': False, 'allow_null': True},
            'max_marks': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        obtained = attrs.get('marks_obtained')
        maximum = attrs.get('max_marks')
        if obtained is not None and maximum is not None and float(obtained) > float(maximum):
            raise serializers.ValidationError(
                {'marks_obtained': 'Marks obtained cannot be more than the maximum marks.'}
            )
        # A subject that is not in the programme's list still needs a label.
        if not attrs.get('subject') and not attrs.get('subject_name'):
            raise serializers.ValidationError(
                {'subject': 'Choose a subject, or type its name.'}
            )
        return attrs

    def create(self, validated_data):
        return SubjectMark.objects.create(**validated_data)


class StudentResultSerializer(serializers.ModelSerializer):
    # Not required: a student is often added to the class list first and given
    # subject marks afterwards, so an empty marks array is a valid state.
    marks = SubjectMarkSerializer(many=True, required=False)
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentResult
        fields = [
            'id', 'exam', 'student_name', 'roll_number', 'total_score',
            'max_score', 'grade', 'remark', 'order', 'percentage', 'marks',
        ]

    def get_percentage(self, obj):
        return obj.percentage

    def validate(self, attrs):
        marks = attrs.get('marks')
        total = attrs.get('total_score')
        maximum = attrs.get('max_score')
        if total is not None and maximum is not None and float(total) > float(maximum):
            raise serializers.ValidationError(
                {'total_score': 'The total score cannot be more than the maximum score.'}
            )
        if marks:
            summed = sum(float(m.get('marks_obtained') or 0) for m in marks)
            summed_max = sum(float(m.get('max_marks') or 0) for m in marks)
            # Totals are only derived from the parts when there is no overall
            # score of the author's own. On an update the field is absent from
            # the payload unless it is being changed, so a typed-in total is
            # never clobbered by editing one subject's mark.
            creating = self.instance is None
            if summed and (creating or 'total_score' in attrs) and attrs.get('total_score') is None:
                attrs['total_score'] = summed
            if summed_max and (creating or 'max_score' in attrs) and attrs.get('max_score') is None:
                attrs['max_score'] = summed_max
        return attrs

    def create(self, validated_data):
        marks = validated_data.pop('marks', [])
        result = StudentResult.objects.create(**validated_data)
        SubjectMark.objects.bulk_create(
            [SubjectMark(result=result, **m) for m in marks]
        )
        return result

    def update(self, instance, validated_data):
        # A nested write is all-or-nothing, so the marks are replaced wholesale
        # rather than merged, which keeps the totals predictable.
        marks = validated_data.pop('marks', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if marks is not None:
            instance.marks.all().delete()
            SubjectMark.objects.bulk_create(
                [SubjectMark(result=instance, **m) for m in marks]
            )
        return instance


class ExamSerializer(serializers.ModelSerializer):
    results = StudentResultSerializer(many=True, read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    subject_count = serializers.SerializerMethodField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=None,
                                  style={'base_template': 'textarea.html'})

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'programme', 'school_class', 'class_name', 'term', 'academic_year',
            'result_file_url', 'notes', 'is_published', 'created_at',
            'total_students', 'subject_count', 'results',
        ]
        extra_kwargs = {
            # Optional, and inferred from class_name when left blank so a
            # session entered as plain text still lands on the right class.
            'school_class': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Keep the display name in step with the class it points at, so the
        # list and the teacher scoping can never disagree.
        school_class = attrs.get('school_class', getattr(self.instance, 'school_class', None))
        if school_class and not attrs.get('class_name'):
            attrs['class_name'] = school_class.name
        return attrs

    def get_subject_count(self, obj):
        """How many distinct subjects this exam actually has marks for."""
        marks = SubjectMark.objects.filter(result__exam=obj)
        return marks.values('subject_id', 'subject_name').distinct().count()

    def validate_notes(self, value):
        return sanitize_html(value or '')


class ExamListSerializer(serializers.ModelSerializer):
    """Exam without its student rows, for the tab's list view."""

    total_students = serializers.IntegerField(read_only=True)
    programme_name = serializers.CharField(source='programme.name', read_only=True, default=None)

    class Meta:
        model = Exam
        # No student rows here: the public listing only advertises that a
        # session exists and where to get the sheet, not who passed.
        fields = [
            'id', 'title', 'programme', 'programme_name', 'school_class', 'class_name', 'term',
            'academic_year', 'result_file_url', 'is_published', 'total_students',
            'created_at',
        ]


class SchoolClassSerializer(serializers.ModelSerializer):
    """
    A class group, with the names an administrator needs to pick one.

    ``class_teacher`` is writable so the admin can put exactly one teacher in
    charge of the class. Writing it moves that person into the class's teacher
    list and hands them the class-teacher role, retiring whoever held it before.
    """

    programme_name = serializers.CharField(source='programme.name', read_only=True, default=None)
    class_teacher = serializers.PrimaryKeyRelatedField(
        queryset=AdminUser.objects.filter(role='teacher', is_active=True),
        allow_null=True,
        required=False,
        help_text='The single teacher in charge of this class.',
    )
    class_teacher_name = serializers.SerializerMethodField()
    teacher_count = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = [
            'id', 'name', 'programme', 'programme_name', 'is_active', 'order',
            'class_teacher', 'class_teacher_name', 'teacher_count', 'student_count',
        ]

    def get_student_count(self, obj):
        if not hasattr(obj, 'active_student_count'):
            return 0
        return obj.active_student_count

    def get_class_teacher_name(self, obj):
        teacher = obj.class_teacher
        return teacher.display_name if teacher else None

    def get_teacher_count(self, obj):
        rows = getattr(obj, '_prefetched_assignments', None)
        if rows is not None:
            return len(rows)
        return obj.teacher_assignments.filter(is_active=True).count()

    def _apply_class_teacher(self, school_class, teacher):
        """
        Point the class at one teacher. The previous holder keeps teaching the
        class but loses the class-teacher role, which is what "only one" means.
        """
        ClassTeacher.objects.filter(
            school_class=school_class, is_class_teacher=True, is_active=True
        ).update(is_class_teacher=False)
        if teacher is not None:
            ClassTeacher.objects.update_or_create(
                teacher=teacher,
                school_class=school_class,
                defaults={'is_active': True, 'is_class_teacher': True},
            )
        # The prefetched rows are a snapshot from before the write, so drop them
        # to make the response reflect what was just changed.
        school_class._prefetched_assignments = None

    def create(self, validated_data):
        teacher = validated_data.pop('class_teacher', None)
        school_class = super().create(validated_data)
        self._apply_class_teacher(school_class, teacher)
        return school_class

    def update(self, instance, validated_data):
        # Only act when the admin actually sent the field, so a partial update
        # of just the name never silently clears the class teacher.
        if 'class_teacher' in self.initial_data:
            teacher = validated_data.pop('class_teacher', None)
        else:
            teacher = None
        school_class = super().update(instance, validated_data)
        if 'class_teacher' in self.initial_data:
            self._apply_class_teacher(school_class, teacher)
        return school_class


class TeachingSlotSerializer(serializers.ModelSerializer):
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='school_class.name', read_only=True)
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    programme_name = serializers.SerializerMethodField()
    is_one_off = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeachingSlot
        fields = [
            'id', 'teacher', 'teacher_username', 'teacher_name', 'school_class', 'class_name',
            'subject', 'subject_name', 'subject_code', 'programme_name',
            'day_of_week', 'day_label', 'date', 'is_one_off', 'start_time', 'end_time', 'room',
        ]
        # Only an administrator writes to this, and they have to say which
        # teacher the period belongs to, so the field is a normal input.
        extra_kwargs = {
            'teacher': {'required': True},
            # Left off the form for a weekly period, which is the usual case.
            'date': {'required': False, 'allow_null': True},
            # A dated period takes its weekday from its date, so it is not asked
            # for. `validate` below still refuses a weekly period with no weekday.
            'day_of_week': {'required': False},
        }

    def get_unique_together_constraints(self, model):
        """
        No generated uniqueness validators for the timetable.

        A clash is explained in words by `_teacher_clash`, which also knows that
        a dated lesson collides with the weekly period it lands on and the day it
        names. The generated validators would run first and answer with a bare
        "the fields teacher, school_class, date, start_time must make a unique
        set", which tells the administrator nothing. The database constraints
        stay in place as the backstop for two saves arriving at the same moment.
        """
        return ()

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username

    def get_programme_name(self, obj):
        programme = obj.subject.programme
        return programme.name if programme else None

    def _record_teaching(self, slot):
        """
        Make sure the teacher counts as teaching that class.

        A period is the one thing that proves a teacher works in a class, and the
        dashboard, the class list and the result scoping all read the class
        assignment rather than the timetable. Without this a teacher could be
        timetabled all week and still see an empty portal.

        The row is created with is_class_teacher left alone: being timetabled
        somewhere never makes someone the class teacher, and never demotes the
        one who already is.
        """
        if slot.teacher_id and slot.school_class_id:
            ClassTeacher.objects.update_or_create(
                teacher_id=slot.teacher_id,
                school_class_id=slot.school_class_id,
                # is_class_teacher is deliberately absent, so an existing row
                # keeps whatever role it already had.
                defaults={'is_active': True},
            )

    def create(self, validated_data):
        slot = super().create(validated_data)
        self._record_teaching(slot)
        return slot

    def update(self, instance, validated_data):
        slot = super().update(instance, validated_data)
        self._record_teaching(slot)
        return slot

    def validate_subject(self, value):
        # A retired subject should not be schedulable, even though the row stays
        # on old periods.
        if not value.is_active:
            raise serializers.ValidationError(
                f'"{value.name}" is hidden. Make it active before scheduling it.'
            )
        return value

    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_time': 'The end time must be after the start time.'}
            )

        instance = self.instance
        # A dated period is filed under the weekday that date actually falls on,
        # so the day can never contradict the date and every "Friday" grouping
        # and clash rule keeps working. A weekly period keeps the chosen weekday,
        # and has to have one, because there is no date to work it out from.
        date = attrs['date'] if 'date' in attrs else getattr(instance, 'date', None)
        day = date.weekday() if date else attrs.get('day_of_week', getattr(instance, 'day_of_week', None))
        if date:
            attrs['day_of_week'] = day
        elif day is None:
            raise serializers.ValidationError(
                {'day_of_week': 'Choose which day this period runs on.'}
            )

        teacher = attrs.get('teacher', getattr(instance, 'teacher', None))
        clash = self._teacher_clash(teacher, start, date, day)
        if clash:
            if date:
                raise serializers.ValidationError(
                    {'start_time': (
                        f'This teacher already has a {clash.subject.name} period starting at '
                        f'that time on {date:%d %B %Y}.'
                    )}
                )
            raise serializers.ValidationError(
                'This teacher already has a period starting at that time on that day.'
            )
        return attrs

    def _teacher_clash(self, teacher, start_time, date, day_of_week):
        """
        The period already on file that would put this teacher in two places at
        once, if there is one.

        A teacher cannot be in two rooms at once, so a clash is refused whatever
        class the two periods are for. Class clashes are allowed, because the
        timetable records what was planned, not what happened.

        A dated lesson is checked against the other lessons that actually fall on
        that date, which is both the dated ones on it and the weekly ones whose
        weekday matches, because those weekly periods do run that day.
        """
        if not (teacher and start_time):
            return None

        slots = TeachingSlot.objects.select_related('subject').filter(
            teacher=teacher, start_time=start_time
        )
        if self.instance:
            slots = slots.exclude(pk=self.instance.pk)
        if date:
            return slots.filter(Q(date=date) | Q(date__isnull=True, day_of_week=day_of_week)).first()
        return slots.filter(date__isnull=True, day_of_week=day_of_week).first()


class StudentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='school_class.name', read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'school_class', 'class_name', 'name', 'roll_number', 'is_active']
        # The unique constraint on (class, roll) makes DRF build a validator that
        # insists the roll is always supplied, which is wrong: plenty of pupils
        # have no roll number yet, and validate() below already reports a
        # duplicate properly. The database constraint still guards the data.
        validators = []
        extra_kwargs = {
            'school_class': {'required': True},
            'roll_number': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        school_class = attrs.get('school_class', getattr(self.instance, 'school_class', None))
        roll = (attrs.get('roll_number', getattr(self.instance, 'roll_number', '')) or '').strip()
        if roll:
            clash = Student.objects.filter(
                school_class=school_class, roll_number=roll
            ).exclude(pk=self.instance.pk) if self.instance else Student.objects.filter(
                school_class=school_class, roll_number=roll
            )
            if clash.exists():
                raise serializers.ValidationError(
                    {'roll_number': f'Roll number {roll} is already used in {school_class.name}.'}
                )
        if not (attrs.get('name', getattr(self.instance, 'name', '')) or '').strip():
            raise serializers.ValidationError({'name': 'A student name is required.'})
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    class_name = serializers.CharField(source='student.school_class.name', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.get_full_name', read_only=True, default=None)

    class Meta:
        model = Attendance
        fields = ['id', 'student', 'student_name', 'roll_number', 'class_name', 'date',
                  'status', 'note', 'marked_by', 'marked_by_name']
        # Marking is a bulk operation keyed on the student, so student and date
        # always arrive in the payload.
        extra_kwargs = {
            'student': {'required': True},
            'date': {'required': True},
            'marked_by': {'required': False, 'read_only': True},
        }

    def validate(self, attrs):
        student = attrs.get('student', getattr(self.instance, 'student', None))
        if student and not student.is_active:
            raise serializers.ValidationError(
                {'student': f'{student.name} has left the class and cannot be marked.'}
            )
        # Saturday is the school's holiday, so nobody can be present.
        date = attrs.get('date', getattr(self.instance, 'date', None))
        if date and date.weekday() == 5:
            raise serializers.ValidationError(
                {'date': 'Saturday is a holiday, so attendance is not taken.'}
            )
        return attrs
