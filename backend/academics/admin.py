from django.contrib import admin
from .models import Programme, Subject, AcademicDocument


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1
    fields = ['name', 'code', 'description', 'order']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'duration', 'is_active', 'order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    search_fields = ['name', 'level']
    inlines = [SubjectInline]


@admin.register(AcademicDocument)
class AcademicDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'programme', 'uploaded_at']
    list_filter = ['programme']
    search_fields = ['title']
