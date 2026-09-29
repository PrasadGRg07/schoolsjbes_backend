from rest_framework import serializers
from config.html import sanitize_html
from .models import HomeHero


class HomeHeroSerializer(serializers.ModelSerializer):
    # Hero copy is authored in the rich-text editor, so it arrives as HTML. The
    # API is authenticated but not admin-only, so the same allowlist sanitiser
    # used by the other content apps is applied before anything is stored.
    stats = serializers.JSONField(required=False)

    class Meta:
        model = HomeHero
        fields = '__all__'

    def validate_eyebrow(self, value):
        return sanitize_html(value or '')

    def validate_heading(self, value):
        return sanitize_html(value or '')

    def validate_intro(self, value):
        return sanitize_html(value or '')
