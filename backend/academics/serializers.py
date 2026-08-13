from rest_framework import serializers
from .models import Programme, Subject, AcademicDocument


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'


class ProgrammeSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)

    class Meta:
        model = Programme
        fields = '__all__'


class AcademicDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicDocument
        fields = '__all__'
