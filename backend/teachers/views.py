from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser

from academics.models import ClassTeacher, SchoolClass
from accounts.permissions import IsAdminOrReadOnly
from .models import Teacher
from .serializers import TeacherAccountSerializer, TeacherAdminSerializer, TeacherSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    """
    Staff records for the website.

    Anyone signed in may read published records, but the draft and unpublished
    ones that a teacher is still filling in are for staff eyes only, so they
    cannot be read by another teacher or scraped without a login.
    """

    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'designation', 'department', 'subject', 'email']
    ordering_fields = ['order', 'name']

    def get_serializer_class(self):
        # The owning login is only useful to, and only safe for, staff.
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return TeacherAdminSerializer
        return TeacherSerializer

    def get_queryset(self):
        qs = Teacher.objects.all()
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        # Claiming a record that a teacher already owns from the admin side would
        # hand the same person two entries, so the link is dropped here.
        serializer.save(user_account=None)


class TeacherAccountViewSet(viewsets.ViewSet):
    """
    The roster of teacher logins, for administrators.

    A teacher is invisible on the staff list until they save a profile, so this
    endpoint lists the accounts themselves and reports how far each profile has
    been filled in. Staff only: a teacher has no business reading the roster.
    """

    permission_classes = [IsAdminUser]
    serializer_class = TeacherAccountSerializer

    def get_queryset(self):
        from accounts.models import AdminUser
        return AdminUser.objects.filter(role='teacher').select_related('teacher_profile').order_by('username')

    def list(self, request):
        return Response(TeacherAccountSerializer(self.get_queryset(), many=True).data)

    def partial_update(self, request, pk=None):
        """
        Lets an administrator switch a teacher login off and decide whether that
        teacher's profile appears on the website.
        """
        account = self.get_queryset().filter(pk=pk).first()
        if account is None:
            return Response({'detail': 'No such teacher account.'}, status=404)

        if 'is_active' in request.data:
            account.is_active = bool(request.data['is_active'])
            account.save(update_fields=['is_active'])

        if 'publish_profile' in request.data:
            profile = account.teacher_profile
            if profile is None:
                return Response(
                    {'detail': 'This teacher has not set up a profile yet.'},
                    status=400,
                )
            profile.is_active = bool(request.data['publish_profile'])
            profile.save(update_fields=['is_active'])

        if 'class_ids' in request.data:
            wanted = request.data['class_ids']
            if not isinstance(wanted, list):
                return Response(
                    {'class_ids': 'Send the class ids as a list.'},
                    status=400,
                )
            known = set(
                SchoolClass.objects.filter(pk__in=[c for c in wanted if c is not None])
                .values_list('pk', flat=True)
            )
            unknown = [c for c in wanted if c not in known]
            if unknown:
                return Response({'class_ids': f'Unknown class ids: {unknown}'}, status=400)

            # Only the classes that were ticked stay assigned; the rest are
            # switched off rather than deleted, so the history survives.
            ClassTeacher.objects.filter(teacher=account).exclude(
                school_class_id__in=known
            ).update(is_active=False)
            ClassTeacher.objects.filter(
                teacher=account, school_class_id__in=known
            ).update(is_active=True)
            for class_id in known:
                ClassTeacher.objects.get_or_create(
                    teacher=account, school_class_id=class_id, defaults={'is_active': True}
                )

        account.refresh_from_db()
        return Response(TeacherAccountSerializer(account).data)