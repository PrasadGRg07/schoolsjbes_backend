from rest_framework import serializers
from .models import HomeHero


class HomeHeroSerializer(serializers.ModelSerializer):
    stats = serializers.JSONField(required=False)

    class Meta:
        model = HomeHero
        fields = '__all__'
