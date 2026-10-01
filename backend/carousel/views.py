from rest_framework import viewsets, mixins
from accounts.permissions import IsAdminOrReadOnly, PublishedOnlyMixin
from .models import TextSlide, ImageSlide
from .serializers import TextSlideSerializer, ImageSlideSerializer


class TextSlideViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_enabled': True}
    serializer_class = TextSlideSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = TextSlide.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_enabled=True)
        return self.apply_published_only(qs)


class ImageSlideViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_enabled': True}
    serializer_class = ImageSlideSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = ImageSlide.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_enabled=True)
        return self.apply_published_only(qs)
