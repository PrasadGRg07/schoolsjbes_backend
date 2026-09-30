from django.urls import path
from .views import (
    AdminProfileView,
    ChangePasswordView,
    CloudinaryUploadView,
    TeacherTokenObtainPairView,
)

urlpatterns = [
    path('me/', AdminProfileView.as_view(), name='admin_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('upload/', CloudinaryUploadView.as_view(), name='cloudinary_upload'),
    # The teacher sign-in door. Grants a token only to a role='teacher' account.
    path('teacher/token/', TeacherTokenObtainPairView.as_view(), name='teacher_token_obtain_pair'),
]
