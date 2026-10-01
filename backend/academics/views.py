from django.db import models, transaction
from django.utils import timezone
from rest_framework import serializers, viewsets, filters
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from accounts.permissions import IsAdminOrReadOnly, IsTeacherOrReadOnly, PublishedOnlyMixin
from .models import (
    Programme, Subject, SubjectFile, AcademicDocument,
    Exam, StudentResult, SubjectMark, SchoolClass, ClassTeacher, TeachingSlot,
    Student, Attendance,
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
    SchoolClassSerializer,
    TeachingSlotSerializer,
    StudentSerializer,
    AttendanceSerializer,
)


class ProgrammeViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_active': True}
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Programme.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True)
        return self.apply_published_only(qs)


class SubjectViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    """Subjects, optionally narrowed to one programme with ?programme=<id>."""

    public_filter = {'is_active': True, 'programme__is_active': True}
    serializer_class = SubjectSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Subject.objects.select_related('programme').prefetch_related('files')
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_active=True, programme__is_active=True)
        programme = self.request.query_params.get('programme')
        if programme:
            qs = qs.filter(programme_id=programme)
        return self.apply_published_only(qs)

    def destroy(self, request, *args, **kwargs):
        # TeachingSlot protects the subject, so a subject on the timetable is
        # refused with an explanation rather than a database error.
        subject = self.get_object()
        periods = subject.timetable_slots.count()
        if periods:
            return Response(
                {
                    'detail': (
                        f'"{subject.name}" is used in {periods} timetable '
                        f'period{"s" if periods != 1 else ""}. Remove those '
                        f'periods first, or hide the subject instead.'
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

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
    permission_classes = [IsAdminOrReadOnly]
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
    permission_classes = [IsAdminOrReadOnly]
    queryset = AcademicDocument.objects.all()


class ExamViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    """
    Result sessions. Both the admin and the public get the summary shape on
    list and retrieve, so opening the tab does not pull every student mark for
    every session at once. An admin drilling into a session gets its student
    rows from the full serializer, and individual marks are reached through the
    result lookup, which requires a roll number or name when called publicly.
    """

    public_filter = {'is_published': True, 'programme__is_active': True}
    permission_classes = [IsAdminOrReadOnly]

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
        qs = self.apply_published_only(qs)
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


class StudentResultViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'exam__is_published': True, 'exam__programme__is_active': True}
    """
    Students within an exam, narrowed with ?exam=<id>.

    A public visitor may look up a single student by roll number or name, which
    is what makes a "check my result" page possible without exposing the sheet.
    The lookup filters are required for anonymous callers so the whole class
    list cannot simply be walked by paging through the endpoint.

    A teacher is further limited to the classes they have been given, so a
    teacher token cannot read or edit another teacher's students.
    """

    serializer_class = StudentResultSerializer
    permission_classes = [IsTeacherOrReadOnly]

    def get_teacher_class_ids(self):
        """Classes this teacher is in charge of, or None for an admin."""
        user = self.request.user
        if user.is_staff or not user.is_authenticated:
            return None
        return list(
            user.class_assignments.filter(is_active=True)
            .values_list('school_class_id', flat=True)
        )

    def get_queryset(self):
        qs = StudentResult.objects.select_related('exam', 'exam__programme').prefetch_related(
            'marks__subject',
        )
        qs = self.apply_published_only(qs)
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
        teacher_classes = self.get_teacher_class_ids()
        if teacher_classes is not None:
            qs = qs.filter(exam__school_class_id__in=teacher_classes)
        return qs

    def perform_create(self, serializer):
        exam = serializer.validated_data['exam']
        teacher_classes = self.get_teacher_class_ids()
        if teacher_classes is not None and exam.school_class_id not in teacher_classes:
            raise serializers.ValidationError(
                {'exam': 'You can only add results for a class you teach.'}
            )
        # Append to the bottom of the class list.
        if not serializer.validated_data.get('order'):
            last = StudentResult.objects.filter(
                exam=exam,
            ).order_by('-order').first()
            serializer.save(order=(last.order + 1) if last else 1)


class SubjectMarkViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'result__exam__is_published': True}
    """
    Per-subject marks, narrowed with ?result=<id>.

    The public never browses this endpoint; marks reach a visitor nested inside
    the roll-number lookup, so an anonymous call has to name the student whose
    marks it wants or it gets nothing. A teacher is limited to the marks of
    students in their own classes.
    """

    serializer_class = SubjectMarkSerializer
    permission_classes = [IsTeacherOrReadOnly]

    def get_teacher_class_ids(self):
        user = self.request.user
        if user.is_staff or not user.is_authenticated:
            return None
        return list(
            user.class_assignments.filter(is_active=True)
            .values_list('school_class_id', flat=True)
        )

    def get_queryset(self):
        qs = SubjectMark.objects.select_related('subject', 'result', 'result__exam')
        if not self.request.user.is_authenticated:
            qs = qs.filter(result__exam__is_published=True)
        qs = self.apply_published_only(qs)
        result = self.request.query_params.get('result')
        if result:
            qs = qs.filter(result_id=result)
        if not self.request.user.is_authenticated and not result:
            return qs.none()
        teacher_classes = self.get_teacher_class_ids()
        if teacher_classes is not None:
            qs = qs.filter(result__exam__school_class_id__in=teacher_classes)
        return qs

    def perform_create(self, serializer):
        parent = serializer.validated_data.get('result')
        # A mark on its own has to say which student it belongs to.
        if not parent:
            raise serializers.ValidationError(
                {'result': 'A mark must belong to a student result.'}
            )
        teacher_classes = self.get_teacher_class_ids()
        if teacher_classes is not None and parent.exam.school_class_id not in teacher_classes:
            raise serializers.ValidationError(
                {'result': 'You can only add marks for a class you teach.'}
            )
        serializer.save()


class SchoolClassViewSet(viewsets.ModelViewSet):
    """
    The class groups a teacher can be given charge of.

    The timetable and the assignment picker both read from here. Anonymous
    callers are limited to active classes, because these names are published on
    the result sheets anyway.
    """

    serializer_class = SchoolClassSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'programme__name']
    ordering_fields = ['order', 'name']

    def get_queryset(self):
        # The class-teacher row is read on every row, so fetch it up front
        # instead of letting each row run its own query.
        qs = (
            SchoolClass.objects.select_related('programme')
            # Counted in the database rather than in Python, so a page of
            # classes stays a handful of queries instead of one per class.
            .annotate(
                active_student_count=models.Count(
                    'students', filter=models.Q(students__is_active=True), distinct=True,
                )
            )
            .prefetch_related(
                models.Prefetch(
                    'teacher_assignments',
                    queryset=ClassTeacher.objects.filter(is_active=True).select_related('teacher'),
                    to_attr='_prefetched_assignments',
                )
            )
        )
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        return qs


class TeachingSlotViewSet(viewsets.ModelViewSet):
    """
    The weekly timetable.

    Everyone who is signed in may read it, but a teacher only ever sees their
    own periods while an administrator sees the whole school. Only an
    administrator builds or changes the timetable, because it is a school-wide
    plan rather than something a teacher sets privately.
    """

    serializer_class = TeachingSlotSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['subject__name', 'teacher__username', 'teacher__first_name', 'school_class__name']
    ordering_fields = ['day_of_week', 'start_time', 'end_time']

    def get_queryset(self):
        qs = TeachingSlot.objects.select_related('teacher', 'school_class', 'school_class__programme')
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            qs = qs.filter(teacher=user)
        return qs


def teacher_class_ids(user):
    """The classes a teacher currently works in, class teacher or not."""
    return list(
        ClassTeacher.objects
        .filter(teacher=user, is_active=True)
        .values_list('school_class_id', flat=True)
    )


class StudentViewSet(viewsets.ModelViewSet):
    """
    The class roster.

    A teacher reads the students of the classes they are assigned to, because
    taking attendance needs to know who is in the room. Writing is an
    administrator's job: the roster is the school's record of who is enrolled.
    """

    serializer_class = StudentSerializer
    permission_classes = [IsTeacherOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'roll_number']
    ordering_fields = ['roll_number', 'name']

    def get_queryset(self):
        qs = Student.objects.select_related('school_class')
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            qs = qs.filter(school_class_id__in=teacher_class_ids(user))
        school_class = self.request.query_params.get('school_class')
        if school_class:
            qs = qs.filter(school_class_id=school_class)
        if self.request.query_params.get('include_inactive') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    def get_permissions(self):
        # The read-only permission classes are not enough here: a teacher must
        # not be able to enroll or remove pupils by any route.
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrReadOnly()]
        return super().get_permissions()


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Daily attendance.

    Reading is scoped to the teacher's own classes. Marking is allowed for any
    class the teacher is assigned to, because taking the register is part of
    their job, but the roster itself stays under the administrator's control.
    """

    serializer_class = AttendanceSerializer
    permission_classes = [IsTeacherOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date']

    def get_queryset(self):
        qs = Attendance.objects.select_related(
            'student', 'student__school_class', 'marked_by'
        )
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            qs = qs.filter(student__school_class_id__in=teacher_class_ids(user))
        school_class = self.request.query_params.get('school_class')
        if school_class:
            qs = qs.filter(student__school_class_id=school_class)
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(date=date)
        return qs

    def _may_mark(self, school_class_id):
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            return school_class_id in teacher_class_ids(user)
        return True

    @action(detail=False, methods=['get'])
    def sheet(self, request):
        """
        The register for one class on one date: every student with the status
        already recorded, so the grid can show Present next to Absent.
        """
        school_class = request.query_params.get('school_class')
        date = request.query_params.get('date')
        if not school_class or not date:
            return Response(
                {'detail': 'Both school_class and date are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self._may_mark(int(school_class)):
            return Response(
                {'detail': 'You are not assigned to this class.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        students = Student.objects.filter(
            school_class_id=school_class, is_active=True
        ).select_related('school_class')
        recorded = {
            row.student_id: row
            for row in Attendance.objects.filter(
                student__school_class_id=school_class, date=date
            ).select_related('marked_by')
        }
        def register_row(student):
            """One line of the register: the student plus what was recorded."""
            row = recorded.get(student.id)
            marker = row.marked_by if row else None
            return {
                'id': student.id,
                'name': student.name,
                'roll_number': student.roll_number,
                'status': row.status if row else '',
                'note': row.note if row else '',
                'marked_by': (
                    (marker.get_full_name() or marker.username) if marker else ''
                ),
            }

        return Response({
            'school_class': int(school_class),
            'date': date,
            'is_holiday': timezone.datetime.strptime(date, '%Y-%m-%d').weekday() == 5,
            'students': [register_row(student) for student in students],
        })

    @action(detail=False, methods=['post'])
    def mark(self, request):
        """
        Save a whole register in one go.

        Re-marking a student updates that day rather than adding a second row,
        so a teacher who corrects a mistake does not double-count anyone.
        """
        school_class = request.data.get('school_class')
        date = request.data.get('date')
        entries = request.data.get('entries') or []
        if not school_class or not date:
            return Response(
                {'detail': 'Both school_class and date are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self._may_mark(int(school_class)):
            return Response(
                {'detail': 'You are not assigned to this class.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            parsed_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'date': 'Use the format YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if parsed_date.weekday() == 5:
            return Response(
                {'date': 'Saturday is a holiday, so attendance is not taken.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        students = {
            student.id: student
            for student in Student.objects.filter(
                school_class_id=school_class, is_active=True
            ).select_related('school_class')
        }
        # Check the whole register before writing any of it. Saving first and
        # complaining afterwards would leave a half-marked day behind, and the
        # teacher would have no way of telling which half landed.
        unknown = []
        usable = []
        for entry in entries:
            student_id = entry.get('student')
            status_value = entry.get('status')
            if student_id not in students:
                if student_id is not None:
                    unknown.append(student_id)
                continue
            if status_value in dict(Attendance.STATUS):
                usable.append((student_id, status_value, entry.get('note') or ''))
        if unknown:
            return Response(
                {'detail': f'Some students are not in this class: {unknown}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        marker = request.user if request.user.is_authenticated else None
        with transaction.atomic():
            for student_id, status_value, note in usable:
                Attendance.objects.update_or_create(
                    student_id=student_id,
                    date=parsed_date,
                    defaults={
                        'status': status_value,
                        'note': note[:200],
                        'marked_by': marker,
                    },
                )
        return Response({
            'saved': len(usable), 'date': date, 'school_class': int(school_class),
        })

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        Which dates in a range have attendance, so the timetable calendar can
        colour them. Counts come back with the dates so the day can also show
        how many were in.
        """
        start = request.query_params.get('from')
        end = request.query_params.get('to')
        if not start or not end:
            return Response(
                {'detail': 'Both from and to are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rows = (
            self.get_queryset()
            .filter(date__gte=start, date__lte=end)
            .values('date')
            .annotate(
                present=models.Count('id', filter=models.Q(status='present')),
                absent=models.Count('id', filter=models.Q(status='absent')),
                total=models.Count('id'),
            )
            .order_by('date')
        )
        return Response({
            'from': start,
            'to': end,
            'days': [
                {
                    'date': row['date'].isoformat(),
                    'present': row['present'],
                    'absent': row['absent'],
                    'total': row['total'],
                }
                for row in rows
            ],
        })
