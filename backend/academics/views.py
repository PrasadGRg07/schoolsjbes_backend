from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Programme, AcademicDocument
from .serializers import ProgrammeSerializer, AcademicDocumentSerializer


class ProgrammeViewSet(viewsets.ModelViewSet):
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Programme.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True)
        return qs


class AcademicDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicDocumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = AcademicDocument.objects.all()
