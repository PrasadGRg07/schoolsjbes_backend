from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Programme, Subject, SubjectFile, AcademicDocument
from .serializers import (
    ProgrammeSerializer,
    SubjectSerializer,
    SubjectFileSerializer,
    AcademicDocumentSerializer,
)


class ProgrammeViewSet(viewsets.ModelViewSet):
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Programme.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True)
        return qs


class SubjectViewSet(viewsets.ModelViewSet):
    """Subjects, optionally narrowed to one programme with ?programme=<id>."""

    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Subject.objects.select_related('programme').prefetch_related('files')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True, programme__is_active=True)
        programme = self.request.query_params.get('programme')
        if programme:
            qs = qs.filter(programme_id=programme)
        return qs

    def perform_create(self, serializer):
        # Default a new subject to the bottom of its programme's list.
        if not serializer.validated_data.get('order'):
            last = Subject.objects.filter(
                programme=serializer.validated_data['programme']
            ).order_by('-order').first()
            serializer.save(order=(last.order + 1) if last else 1)


class SubjectFileViewSet(viewsets.ModelViewSet):
    """Files belonging to a subject, narrowed with ?subject=<id>."""

    serializer_class = SubjectFileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = SubjectFile.objects.select_related('subject').all()

    def get_queryset(self):
        qs = super().get_queryset()
        subject = self.request.query_params.get('subject')
        if subject:
            qs = qs.filter(subject_id=subject)
        return qs

    def perform_create(self, serializer):
        if not serializer.validated_data.get('order'):
            last = SubjectFile.objects.filter(
                subject=serializer.validated_data['subject']
            ).order_by('-order').first()
            serializer.save(order=(last.order + 1) if last else 1)


class AcademicDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = AcademicDocumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = AcademicDocument.objects.all()
