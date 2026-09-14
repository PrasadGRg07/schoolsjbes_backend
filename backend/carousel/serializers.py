from rest_framework import serializers
from .models import TextSlide, ImageSlide


class TextSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextSlide
        fields = '__all__'


class ImageSlideSerializer(serializers.ModelSerializer):
    resolved_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageSlide
        fields = '__all__'

    def get_resolved_image_url(self, obj):
        url = obj.resolved_image_url()
        if url and url.startswith('/'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(url)
        return url
