from rest_framework import serializers
from .models import AdmissionInfo, AdmissionApplication


class AdmissionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionInfo
        fields = '__all__'


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionApplication
        fields = '__all__'
        read_only_fields = ['status', 'submitted_at', 'updated_at']


class AdmissionApplicationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionApplication
        fields = '__all__'
