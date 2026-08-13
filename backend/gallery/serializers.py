from rest_framework import serializers
from .models import Album, GalleryPhoto


class GalleryPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryPhoto
        fields = '__all__'


class AlbumSerializer(serializers.ModelSerializer):
    photos = GalleryPhotoSerializer(many=True, read_only=True)
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = '__all__'

    def get_photo_count(self, obj):
        return obj.photos.count()


class AlbumListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for album listing (no photos)."""
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ['id', 'title', 'description', 'cover_image_url', 'date', 'photo_count']

    def get_photo_count(self, obj):
        return obj.photos.count()
