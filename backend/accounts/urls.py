from django.urls import path
from .views import AdminProfileView, ChangePasswordView, CloudinaryUploadView

urlpatterns = [
    path('me/', AdminProfileView.as_view(), name='admin_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('upload/', CloudinaryUploadView.as_view(), name='cloudinary_upload'),
]
