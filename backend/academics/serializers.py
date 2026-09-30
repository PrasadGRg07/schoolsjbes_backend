from rest_framework import serializers
from config.html import sanitize_html
from .models import (
    Programme, Subject, SubjectFile, AcademicDocument,
    Exam, StudentResult, SubjectMark,
)


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
