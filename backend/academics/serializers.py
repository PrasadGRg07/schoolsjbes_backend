from rest_framework import serializers
from config.html import sanitize_html
from .models import (
    Programme, Subject, SubjectFile, AcademicDocument,
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


class AcademicDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicDocument
        fields = '__all__'


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

    class Meta:
        model = TeachingSlot
        fields = [
            'id', 'teacher', 'teacher_username', 'teacher_name', 'school_class', 'class_name',
            'subject', 'subject_name', 'subject_code', 'programme_name',
            'day_of_week', 'day_label', 'start_time', 'end_time', 'room',
        ]
        # Only an administrator writes to this, and they have to say which
        # teacher the period belongs to, so the field is a normal input.
        extra_kwargs = {'teacher': {'required': True}}

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
        # A teacher cannot be in two rooms at once. Class clashes are allowed,
        # because the timetable records what was planned, not what happened.
        clash = TeachingSlot.objects.filter(
            teacher=attrs.get('teacher', getattr(self.instance, 'teacher', None)),
            day_of_week=attrs.get('day_of_week', getattr(self.instance, 'day_of_week', None)),
            start_time=start,
        ).exclude(pk=self.instance.pk) if self.instance else TeachingSlot.objects.filter(
            teacher=attrs.get('teacher'),
            day_of_week=attrs.get('day_of_week'),
            start_time=start,
        )
        if clash.exists():
            raise serializers.ValidationError(
                'This teacher already has a period starting at that time on that day.'
            )
        return attrs


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
