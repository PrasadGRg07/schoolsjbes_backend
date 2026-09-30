from rest_framework import serializers

from accounts.models import AdminUser
from .models import Teacher


class TeacherSerializer(serializers.ModelSerializer):
    """The public staff record. Deliberately free of any login details."""

    class Meta:
        model = Teacher
        fields = '__all__'


class TeacherAdminSerializer(serializers.ModelSerializer):
    """
    Adds the login that owns the record, so an administrator can tell which
    staff entries are maintained by a teacher from their own settings page.
    """

    account_username = serializers.SerializerMethodField()
    account_role = serializers.SerializerMethodField()
    managed_by_teacher = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = '__all__'
        read_only_fields = ['account_username', 'account_role', 'managed_by_teacher']

    def _account(self, obj):
        # Nullable relations read back as None rather than raising.
        return getattr(obj, 'user_account', None)

    def get_account_username(self, obj):
        account = self._account(obj)
        return account.username if account else None

    def get_account_role(self, obj):
        account = self._account(obj)
        return account.role if account else None

    def get_managed_by_teacher(self, obj):
        return self._account(obj) is not None


class TeacherAccountSerializer(serializers.ModelSerializer):
    """
    One row per teacher login, so the administrator can see who has a login
    even before that person has filled in a profile of their own.
    """

    full_name = serializers.SerializerMethodField()
    has_profile = serializers.SerializerMethodField()
    profile_id = serializers.SerializerMethodField()
    profile_name = serializers.SerializerMethodField()
    profile_is_active = serializers.SerializerMethodField()
    profile_missing = serializers.SerializerMethodField()
    class_ids = serializers.SerializerMethodField()
    class_names = serializers.SerializerMethodField()
    # The classes where this teacher is the single person in charge, which is
    # not the same as every class they teach in.
    class_teacher_class_ids = serializers.SerializerMethodField()
    class_teacher_class_names = serializers.SerializerMethodField()

    class Meta:
        model = AdminUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name', 'email',
            'is_active', 'last_login', 'has_profile', 'profile_id', 'profile_name',
            'profile_is_active', 'profile_missing', 'class_ids', 'class_names',
            'class_teacher_class_ids', 'class_teacher_class_names',
        ]
        read_only_fields = fields

    def get_class_ids(self, obj):
        return [c.school_class_id for c in obj.class_assignments.filter(is_active=True)]

    def get_class_names(self, obj):
        return [c.school_class.name for c in obj.class_assignments.filter(is_active=True)]

    def get_class_teacher_class_ids(self, obj):
        rows = obj.class_assignments.filter(is_active=True, is_class_teacher=True)
        return [r.school_class_id for r in rows]

    def get_class_teacher_class_names(self, obj):
        rows = obj.class_assignments.filter(is_active=True, is_class_teacher=True)
        return [r.school_class.name for r in rows]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def _profile(self, obj):
        return obj.teacher_profile

    def get_has_profile(self, obj):
        return self._profile(obj) is not None

    def get_profile_id(self, obj):
        profile = self._profile(obj)
        return profile.id if profile else None

    def get_profile_name(self, obj):
        profile = self._profile(obj)
        return profile.name if profile else ''

    def get_profile_is_active(self, obj):
        profile = self._profile(obj)
        return bool(profile and profile.is_active)

    def get_profile_missing(self, obj):
        """The recommended fields still blank, so the admin can nudge the teacher."""
        profile = self._profile(obj)
        if profile is None:
            return ['profile']
        checks = {
            'name': profile.name,
            'designation': profile.designation,
            'subject': profile.subject,
            'email': profile.email,
            'bio': profile.bio,
        }
        return [key for key, value in checks.items() if not (value or '').strip()]