from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchoolClassViewSet,
    TeachingSlotViewSet,
    ProgrammeViewSet,
    SubjectViewSet,
    SubjectFileViewSet,
    AcademicDocumentViewSet,
    ExamViewSet,
    StudentResultViewSet,
    SubjectMarkViewSet,
    StudentViewSet,
    AttendanceViewSet,
)

router = DefaultRouter()
router.register('programmes', ProgrammeViewSet, basename='programme')
router.register('subjects', SubjectViewSet, basename='subject')
router.register('subject-files', SubjectFileViewSet, basename='subject-file')
router.register('documents', AcademicDocumentViewSet, basename='academic-doc')
router.register('exams', ExamViewSet, basename='exam')
router.register('results', StudentResultViewSet, basename='student-result')
router.register('marks', SubjectMarkViewSet, basename='subject-mark')
router.register('classes', SchoolClassViewSet, basename='school-class')
router.register('timetable', TeachingSlotViewSet, basename='teaching-slot')
router.register('students', StudentViewSet, basename='student')
router.register('attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [path('', include(router.urls))]
