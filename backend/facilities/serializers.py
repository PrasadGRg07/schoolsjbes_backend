from rest_framework import serializers
from .models import Facility, FacilityImage


class FacilityImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityImage
        fields = '__all__'


class FacilitySerializer(serializers.ModelSerializer):
    images = FacilityImageSerializer(many=True, read_only=True)

    class Meta:
        model = Facility
        fields = '__all__'
