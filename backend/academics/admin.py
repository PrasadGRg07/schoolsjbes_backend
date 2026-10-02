from django.contrib import admin
from .models import Programme, Subject, Chapter, AcademicDocument, DocumentQuestion


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1
    fields = ['name', 'code', 'description', 'order']


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ['name', 'order', 'is_active']


class DocumentQuestionInline(admin.TabularInline):
    model = DocumentQuestion
    extra = 0
    fields = ['order', 'question', 'question_type', 'options', 'correct_option', 'answer', 'marks', 'explanation']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'duration', 'is_active', 'order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    search_fields = ['name', 'level']
    inlines = [SubjectInline]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'subject__name']


@admin.register(AcademicDocument)
class AcademicDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'programme', 'subject', 'chapter', 'document_type', 'status', 'uploaded_at']
    list_filter = ['programme', 'subject', 'document_type', 'status']
    search_fields = ['title', 'subject__name', 'chapter__name']
    inlines = [DocumentQuestionInline]