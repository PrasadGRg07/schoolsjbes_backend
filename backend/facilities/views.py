from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Facility, FacilityImage
from .serializers import FacilitySerializer, FacilityImageSerializer


class FacilityViewSet(viewsets.ModelViewSet):
    serializer_class = FacilitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Facility.objects.prefetch_related('images').all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True)
        return qs


class FacilityImageViewSet(viewsets.ModelViewSet):
    queryset = FacilityImage.objects.all()
    serializer_class = FacilityImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
