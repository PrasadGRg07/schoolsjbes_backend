from rest_framework import serializers
from config.html import sanitize_html
from .models import Programme, Subject, SubjectFile, AcademicDocument


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
