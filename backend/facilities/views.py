from rest_framework import viewsets
from accounts.permissions import IsAdminOrReadOnly, PublishedOnlyMixin
from .models import Facility, FacilityImage
from .serializers import FacilitySerializer, FacilityImageSerializer


class FacilityViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_active': True}
    serializer_class = FacilitySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Facility.objects.prefetch_related('images').all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True)
        return self.apply_published_only(qs)


class FacilityImageViewSet(viewsets.ModelViewSet):
    queryset = FacilityImage.objects.all()
    serializer_class = FacilityImageSerializer
    permission_classes = [IsAdminOrReadOnly]
