"""
The teacher area's own API: one dashboard call that returns everything the
teacher dashboard needs, scoped to the classes that teacher is in charge of.
"""
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from academics.models import ClassTeacher, Exam, SchoolClass, StudentResult
from accounts.models import AdminUser
from teachers.models import Teacher


def teacher_classes(user):
    """Active classes assigned to this teacher, in display order."""
    return (
        SchoolClass.objects.filter(teachers__teacher=user, teachers__is_active=True)
        .select_related('programme')
        .distinct()
        .order_by('order', 'name')
    )


class TeacherDashboardView(APIView):
    """
    Summary of a teacher's own classes: student totals, the result sessions in
    each class, and how many of those sessions are still unpublished drafts.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_teacher):
            return Response(
                {'detail': 'This account is not a teacher account.'},
                status=403,
            )

        classes = teacher_classes(user)
        class_payload = []
        total_students = 0
        total_sessions = 0
        total_drafts = 0

        for school_class in classes:
            sessions = (
                Exam.objects.filter(school_class=school_class)
                .select_related('programme')
                .prefetch_related('results')
                .order_by('-academic_year', '-created_at')
            )
            student_count = (
                StudentResult.objects.filter(exam__school_class=school_class)
                .values('exam_id')
                .distinct()
                .count()
            )
            # Distinct students across the class's sessions.
            students_in_class = StudentResult.objects.filter(
                exam__school_class=school_class
            ).values('student_name').distinct().count()

            session_payload = [
                {
                    'id': s.id,
                    'title': s.title,
                    'term': s.term,
                    'academic_year': s.academic_year,
                    'is_published': s.is_published,
                    'total_students': s.total_students,
                    'result_file_url': s.result_file_url,
                }
                for s in sessions
            ]

            drafts = sum(1 for s in session_payload if not s['is_published'])
            total_sessions += len(session_payload)
            total_drafts += drafts
            total_students += students_in_class

            class_payload.append({
                'id': school_class.id,
                'name': school_class.name,
                'programme': school_class.programme.name if school_class.programme else None,
                'student_count': students_in_class,
                'session_count': len(session_payload),
                'draft_count': drafts,
                'sessions': session_payload,
            })

        profile = None
        if user.teacher_profile_id:
            tp = user.teacher_profile
            profile = {
                'name': tp.name,
                'designation': tp.designation,
                'subject': tp.subject,
                'department': tp.department,
                'photo_url': tp.photo_url,
            }

        return Response({
            'teacher': {
                'display_name': user.display_name,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            },
            'profile': profile,
            'classes': class_payload,
            'summary': {
                'class_count': len(class_payload),
                'student_count': total_students,
                'session_count': total_sessions,
                'draft_count': total_drafts,
            },
        })


class MyClassesView(APIView):
    """The signed-in teacher's class list, for pickers in the teacher area."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_teacher):
            return Response({'detail': 'This account is not a teacher account.'}, status=403)
        return Response([
            {
                'id': c.id,
                'name': c.name,
                'programme': c.programme.name if c.programme else None,
            }
            for c in teacher_classes(user)
        ])


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    The public-facing staff record that a teacher maintains for themselves.

    This is the same row the admin Teachers page and the website teachers
    section already read, so anything saved here shows up in both without a
    second copy. `order` is left to the administrator because it decides the
    order names appear in.
    """

    class Meta:
        model = Teacher
        fields = [
            'id', 'name', 'designation', 'department', 'subject', 'qualification',
            'experience_years', 'gender', 'joining_date', 'email', 'phone', 'address',
            'bio', 'photo_url', 'facebook_url', 'is_active',
        ]
        read_only_fields = ['id']

    def validate_email(self, value):
        # Blank is allowed, but a second teacher record must not claim the same
        # address, otherwise the contact links on the public page get crossed.
        qs = Teacher.objects.filter(email__iexact=value).exclude(pk=self.instance.pk) if self.instance else Teacher.objects.filter(email__iexact=value)
        if qs.exists():
            raise serializers.ValidationError('Another staff record already uses this email address.')
        return value

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('Your name cannot be empty.')
        return value.strip()


class TeacherProfileView(APIView):
    """
    Lets a teacher fill in the staff record that represents them.

    Reading returns an empty, unpublished record when nothing is linked yet, so
    an untouched account never puts a blank card on the public teachers list.
    The database row is only created once the teacher actually saves.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_teacher):
            return Response({'detail': 'This account is not a teacher account.'}, status=403)
        return Response(self._payload(user))

    def patch(self, request):
        user = request.user
        if not (user.is_staff or user.is_teacher):
            return Response({'detail': 'This account is not a teacher account.'}, status=403)

        # A nullable one-to-one with no row yet reads back as None rather than
        # raising, so this is an explicit None test.
        linked = user.teacher_profile
        if linked is None:
            # A reverse relation cannot be passed to create(), so build the
            # staff row first and then hang the account off it. New records stay
            # off the public site until the teacher publishes them, so nothing
            # half-typed shows up on the website.
            linked = Teacher.objects.create(
                name=(user.get_full_name() or user.username).strip(),
                email=user.email or '',
                is_active=False,
            )
            user.teacher_profile = linked
            user.save(update_fields=['teacher_profile'])

        serializer = TeacherProfileSerializer(linked, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(self._payload(user))

    def _payload(self, user):
        teacher = user.teacher_profile
        linked = teacher is not None
        if not linked:
            # Deliberately left unlinked: attaching an unsaved row to the user
            # would populate Django's relation cache and make the next lookup in
            # this request pretend a record already exists.
            teacher = Teacher(
                name=(user.get_full_name() or user.username).strip(),
                email=user.email or '',
                is_active=False,
            )

        return {
            'linked': linked,
            'username': user.username,
            'role': user.role,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile': TeacherProfileSerializer(teacher).data,
        }
