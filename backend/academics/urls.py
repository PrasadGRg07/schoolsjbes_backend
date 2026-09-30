from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProgrammeViewSet,
    SubjectViewSet,
    SubjectFileViewSet,
    AcademicDocumentViewSet,
)

router = DefaultRouter()
router.register('programmes', ProgrammeViewSet, basename='programme')
router.register('subjects', SubjectViewSet, basename='subject')
router.register('subject-files', SubjectFileViewSet, basename='subject-file')
router.register('documents', AcademicDocumentViewSet, basename='academic-doc')

urlpatterns = [path('', include(router.urls))]
