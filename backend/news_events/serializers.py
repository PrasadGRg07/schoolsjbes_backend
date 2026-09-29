from rest_framework import serializers
from config.html import sanitize_html
from .models import NewsEvent


class NewsEventSerializer(serializers.ModelSerializer):
    content = serializers.CharField(
        required=False, allow_blank=True, max_length=None,
        style={'base_template': 'textarea.html'},
    )

    class Meta:
        model = NewsEvent
        fields = '__all__'

    def validate_content(self, value):
        return sanitize_html(value or '')


class NewsEventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsEvent
        fields = ['id', 'title', 'slug', 'type', 'excerpt', 'cover_image_url', 'event_date', 'created_at', 'show_popup', 'popup_expires_at']
