from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdmissionInfoView, AdmissionApplicationView, AdmissionApplicationAdminViewSet

router = DefaultRouter()
router.register('applications', AdmissionApplicationAdminViewSet, basename='admission-app')

urlpatterns = [
    path('info/', AdmissionInfoView.as_view(), name='admission_info'),
    path('apply/', AdmissionApplicationView.as_view(), name='admission_apply'),
    path('admin/', include(router.urls)),
]
