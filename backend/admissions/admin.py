from django.contrib import admin
from .models import AdmissionInfo, AdmissionApplication


@admin.register(AdmissionInfo)
class AdmissionInfoAdmin(admin.ModelAdmin):
    list_display = ['academic_year', 'open_for_admission', 'deadline', 'updated_at']
    fieldsets = (
        ('Status', {'fields': ('open_for_admission', 'academic_year', 'deadline')}),
        ('Content', {'fields': ('intro', 'eligibility', 'process', 'required_documents', 'fee_structure')}),
    )

    def has_add_permission(self, request):
        return not AdmissionInfo.objects.exists()


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ['student_name', 'grade_applying', 'parent_name', 'parent_phone', 'status', 'submitted_at']
    list_filter = ['status', 'grade_applying', 'gender']
    list_editable = ['status']
    search_fields = ['student_name', 'parent_name', 'parent_phone']
    readonly_fields = ['submitted_at', 'updated_at']
    date_hierarchy = 'submitted_at'
