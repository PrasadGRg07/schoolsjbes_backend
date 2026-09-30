"""
URLs for the teacher area. Mounted at /api/teacher/ so the teacher endpoints
are grouped away from the shared /api/auth/ sign-in routes.
"""
from django.urls import path

from .teacher_views import MyClassesView, TeacherDashboardView

urlpatterns = [
    path('dashboard/', TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('classes/', MyClassesView.as_view(), name='teacher_my_classes'),
]
