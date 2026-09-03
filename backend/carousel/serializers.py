from rest_framework import serializers
from .models import TextSlide, ImageSlide


class TextSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextSlide
        fields = '__all__'


class ImageSlideSerializer(serializers.ModelSerializer):
    resolved_image_url = serializers.CharField(read_only=True)

    class Meta:
        model = ImageSlide
        fields = '__all__'
