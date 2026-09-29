from rest_framework import serializers
from config.html import sanitize_html
from .models import Programme, Subject, AcademicDocument


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class ProgrammeSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)
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
