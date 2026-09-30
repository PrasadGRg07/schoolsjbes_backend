from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherAccountViewSet, TeacherViewSet

router = DefaultRouter()
# Registered before the staff list, otherwise its detail route would swallow
# "accounts/" as a primary key and the roster would 404.
router.register('accounts', TeacherAccountViewSet, basename='teacher-account')
router.register('', TeacherViewSet, basename='teacher')

urlpatterns = [path('', include(router.urls))]