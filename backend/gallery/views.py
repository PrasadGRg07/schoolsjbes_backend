from rest_framework import viewsets
from accounts.permissions import IsAdminOrReadOnly
from .models import Album, GalleryPhoto
from .serializers import AlbumSerializer, AlbumListSerializer, GalleryPhotoSerializer


class AlbumViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return AlbumListSerializer
        return AlbumSerializer

    def get_queryset(self):
        qs = Album.objects.prefetch_related('photos').all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        return qs


class GalleryPhotoViewSet(viewsets.ModelViewSet):
    queryset = GalleryPhoto.objects.all()
    serializer_class = GalleryPhotoSerializer
    permission_classes = [IsAdminOrReadOnly]
