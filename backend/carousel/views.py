from rest_framework import viewsets, mixins
from accounts.permissions import IsAdminOrReadOnly
from .models import TextSlide, ImageSlide
from .serializers import TextSlideSerializer, ImageSlideSerializer


class TextSlideViewSet(viewsets.ModelViewSet):
    serializer_class = TextSlideSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = TextSlide.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_enabled=True)
        return qs


class ImageSlideViewSet(viewsets.ModelViewSet):
    serializer_class = ImageSlideSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = ImageSlide.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_enabled=True)
        return qs
