from rest_framework import serializers
from .models import NewsEvent


class NewsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsEvent
        fields = '__all__'


class NewsEventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsEvent
        fields = ['id', 'title', 'slug', 'type', 'excerpt', 'cover_image_url', 'event_date', 'created_at']
