from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import (
    Programme, Subject, SubjectFile, AcademicDocument,
    Exam, StudentResult, SubjectMark,
)
from .serializers import (
    ProgrammeSerializer,
    SubjectSerializer,
    SubjectFileSerializer,
    AcademicDocumentSerializer,
    ExamSerializer,
    ExamListSerializer,
    StudentResultSerializer,
    SubjectMarkSerializer,
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


class ExamViewSet(viewsets.ModelViewSet):
    """
    Result sessions. Both the admin and the public get the summary shape on
    list and retrieve, so opening the tab does not pull every student mark for
    every session at once. An admin drilling into a session gets its student
    rows from the full serializer, and individual marks are reached through the
    result lookup, which requires a roll number or name when called publicly.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve') or not self.request.user.is_authenticated:
            return ExamListSerializer
        return ExamSerializer

    def get_queryset(self):
        qs = Exam.objects.select_related('programme').prefetch_related(
            'results__marks__subject',
        )
        if not self.request.user.is_authenticated:
            # Unpublished sessions, and any hidden programme they hang off,
            # must not be reachable by guessing an id.
            qs = qs.filter(is_published=True).exclude(
                programme__is_active=False,
            )
        programme = self.request.query_params.get('programme')
        if programme:
            if programme in ('none', 'null'):
                qs = qs.filter(programme__isnull=True)
            else:
                qs = qs.filter(programme_id=programme)
        if self.request.query_params.get('class_name'):
            qs = qs.filter(class_name=self.request.query_params['class_name'])
        if self.request.query_params.get('term'):
            qs = qs.filter(term=self.request.query_params['term'])
        if self.request.query_params.get('academic_year'):
            qs = qs.filter(academic_year=self.request.query_params['academic_year'])
        return qs


class StudentResultViewSet(viewsets.ModelViewSet):
    """
    Students within an exam, narrowed with ?exam=<id>.

    A public visitor may look up a single student by roll number or name, which
    is what makes a "check my result" page possible without exposing the sheet.
    The lookup filters are required for anonymous callers so the whole class
    list cannot simply be walked by paging through the endpoint.
    """

    serializer_class = StudentResultSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = StudentResult.objects.select_related('exam', 'exam__programme').prefetch_related(
            'marks__subject',
        )
        exam = self.request.query_params.get('exam')
        if exam:
            qs = qs.filter(exam_id=exam)
        if not self.request.user.is_authenticated:
            # Only results inside a published exam are visible publicly.
            qs = qs.filter(exam__is_published=True)
        # Single-student lookup, used by the public result checker.
        roll = self.request.query_params.get('roll_number')
        if roll:
            qs = qs.filter(roll_number__iexact=roll.strip())
        name = self.request.query_params.get('student_name')
        if name:
            qs = qs.filter(student_name__icontains=name.strip())
        if not self.request.user.is_authenticated and not (roll or name):
            # No identifying filter means "show me everyone", which is an admin
            # job. An anonymous caller has to name the student it wants.
            return qs.none()
        return qs

    def perform_create(self, serializer):
        # Append to the bottom of the class list.
        if not serializer.validated_data.get('order'):
            last = StudentResult.objects.filter(
                exam=serializer.validated_data['exam'],
            ).order_by('-order').first()
            serializer.save(order=(last.order + 1) if last else 1)


class SubjectMarkViewSet(viewsets.ModelViewSet):
    """
    Per-subject marks, narrowed with ?result=<id>.

    The public never browses this endpoint; marks reach a visitor nested inside
    the roll-number lookup, so an anonymous call has to name the student whose
    marks it wants or it gets nothing.
    """

    serializer_class = SubjectMarkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = SubjectMark.objects.select_related('subject', 'result', 'result__exam')
        if not self.request.user.is_authenticated:
            qs = qs.filter(result__exam__is_published=True)
        result = self.request.query_params.get('result')
        if result:
            qs = qs.filter(result_id=result)
        if not self.request.user.is_authenticated and not result:
            return qs.none()
        return qs

    def perform_create(self, serializer):
        # A mark on its own has to say which student it belongs to.
        if not serializer.validated_data.get('result'):
            raise serializers.ValidationError(
                {'result': 'A mark must belong to a student result.'}
            )
        serializer.save()
