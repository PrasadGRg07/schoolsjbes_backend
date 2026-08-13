from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProgrammeViewSet, AcademicDocumentViewSet

router = DefaultRouter()
router.register('programmes', ProgrammeViewSet, basename='programme')
router.register('documents', AcademicDocumentViewSet, basename='academic-doc')

urlpatterns = [path('', include(router.urls))]
