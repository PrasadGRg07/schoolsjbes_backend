from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AdminUser


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('School Access', {'fields': ('role', 'teacher_profile', 'phone')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    list_filter = UserAdmin.list_filter + ('role',)
    # A teacher only needs enough of Django's user admin to be maintained, and
    # the fields that would hand them the whole site are hidden.
    fieldsets_for_teacher = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('is_active', 'role', 'teacher_profile')}),
    )

    def get_fieldsets(self, request, obj=None):
        # Showing a teacher the "staff"/"superuser" switches would let them
        # promote themselves to admin from this page.
        if obj is not None and obj.is_teacher and not request.user.is_superuser:
            return self.fieldsets_for_teacher
        return super().get_fieldsets(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers manage teachers but cannot edit admin accounts.
            return qs.filter(role=AdminUser.ROLE_TEACHER)
        return qs

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser and obj.role != AdminUser.ROLE_TEACHER:
            return False
        return super().has_delete_permission(request, obj)
