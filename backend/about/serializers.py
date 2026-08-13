from rest_framework import serializers
from .models import PrincipalMessage, SchoolHistory


class PrincipalMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrincipalMessage
        fields = '__all__'


class SchoolHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolHistory
        fields = '__all__'
