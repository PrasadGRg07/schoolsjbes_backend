from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    """
    Staff records for the website. A row that is linked to a teacher account is
    that teacher's own profile and is maintained from the teacher area, so the
    read-only summary below tells the administrator who looks after what.
    """

    list_display = (
        'name', 'designation', 'department', 'subject',
        'linked_account', 'is_active', 'order',
    )
    list_filter = ('is_active', 'department', 'designation')
    search_fields = ('name', 'designation', 'department', 'subject', 'email', 'user_account__username')
    list_editable = ('is_active', 'order')
    ordering = ('order', 'name')
    readonly_fields = ('linked_account', 'created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('name', 'designation', 'department', 'subject', 'photo_url')}),
        ('Contact', {'fields': ('email', 'phone', 'address', 'facebook_url')}),
        ('Details', {'fields': ('qualification', 'experience_years', 'gender', 'joining_date', 'bio')}),
        ('Visibility', {
            'fields': ('is_active', 'order', 'linked_account'),
            'description': 'Inactive records are hidden from the website. '
                           'Display order decides the sequence on the teachers page.',
        }),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Managed by')
    def linked_account(self, obj):
        """Show the login that owns this record, or note that it is admin-only."""
        user = obj.user_account
        return f'{user.username} ({user.role})' if user else '—'