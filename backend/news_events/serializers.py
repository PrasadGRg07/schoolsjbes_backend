from rest_framework import serializers
from config.html import sanitize_html, strip_html
from .models import NewsEvent

# Caps on the text the reader actually sees. The stored markup is allowed to be
# far longer, so these are checked against the stripped text, not the raw value.
TITLE_MAX_CHARS = 300
EXCERPT_MAX_CHARS = 400


def _clean_rich_text(value, label, limit):
    """Sanitise a rich-text field and cap it by visible characters."""
    clean = sanitize_html(value or '')
    visible = len(strip_html(clean))
    if visible > limit:
        raise serializers.ValidationError(
            '%s is %d characters. Please keep it under %d.'
            % (label, visible, limit)
        )
    return clean


class NewsEventSerializer(serializers.ModelSerializer):
    # Declared explicitly so the markup cap is larger than the model's original
    # plain-text cap; DRF copies max_length straight off the model field.
    title = serializers.CharField(max_length=1500)
    excerpt = serializers.CharField(
        required=False, allow_blank=True, max_length=2500,
        style={'base_template': 'textarea.html'},
    )
    content = serializers.CharField(
        required=False, allow_blank=True, max_length=None,
        style={'base_template': 'textarea.html'},
    )

    class Meta:
        model = NewsEvent
        fields = '__all__'

    def validate_title(self, value):
        return _clean_rich_text(value, 'Title', TITLE_MAX_CHARS)

    def validate_excerpt(self, value):
        return _clean_rich_text(value, 'Excerpt', EXCERPT_MAX_CHARS)

    def validate_content(self, value):
        return sanitize_html(value or '')


class NewsEventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsEvent
        # is_published is needed by the admin list, which shows a Published/Hidden
        # badge from it. Without it the field is always undefined and every row
        # renders as "Hidden".
        fields = [
            'id', 'title', 'slug', 'type', 'excerpt', 'cover_image_url',
            'cover_ratio', 'cover_focus_x', 'cover_focus_y',
            'event_date', 'created_at', 'is_published', 'show_popup',
            'popup_expires_at',
        ]
