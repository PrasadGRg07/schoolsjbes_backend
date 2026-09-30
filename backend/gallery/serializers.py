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
        # order/is_published are needed by the admin list (reorder buttons, status badge)
        # cover_* are needed to frame the album card the same way the admin set it up
        fields = [
            'id', 'title', 'description', 'cover_image_url',
            'cover_ratio', 'cover_focus_x', 'cover_focus_y',
            'date', 'is_published', 'order', 'photo_count',
        ]

    def get_photo_count(self, obj):
        return obj.photos.count()
