from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .serializers import AdminProfileSerializer, ChangePasswordSerializer
import cloudinary.uploader

User = get_user_model()


class _RoleCheckedTokenSerializer(TokenObtainPairSerializer):
    """Base for the two sign-in doors, so each one only opens for its own role."""

    #: Subclasses set this to the role this door admits.
    allowed_role = None
    rejection = ''

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.role != self.allowed_role:
            raise serializers.ValidationError({'detail': self.rejection}, code='wrong_role')
        return data


class TeacherTokenObtainPairSerializer(_RoleCheckedTokenSerializer):
    allowed_role = User.ROLE_TEACHER
    rejection = 'This account is not a teacher account. Please use the admin login.'


class AdminTokenObtainPairSerializer(_RoleCheckedTokenSerializer):
    allowed_role = User.ROLE_ADMIN
    rejection = 'This account is not an administrator account. Please use the teacher login.'


class TeacherTokenObtainPairView(TokenObtainPairView):
    serializer_class = TeacherTokenObtainPairSerializer


class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer


class AdminProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = AdminProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = AdminProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not request.user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Old password is incorrect.'}, status=400)
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully.'})
        return Response(serializer.errors, status=400)


class CloudinaryUploadView(APIView):
    """Upload a file to Cloudinary and return the URL."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        folder = request.data.get('folder', 'sjbebs')
        if not file:
            return Response({'error': 'No file provided.'}, status=400)
        from django.conf import settings
        if getattr(settings, 'DEFAULT_FILE_STORAGE', '') == 'django.core.files.storage.FileSystemStorage':
            from django.core.files.storage import default_storage
            import os
            path = default_storage.save(os.path.join(folder, file.name), file)
            url = default_storage.url(path)
            # Make sure url includes host if it's relative
            if url.startswith('/'):
                url = request.build_absolute_uri(url)
            return Response({'url': url, 'public_id': path}, status=201)

        # Cloudinary picks the delivery pipeline from the resource type. Images and
        # videos must use image/video; everything else (pdf, docx, xlsx, zip) has to
        # be uploaded as 'raw', otherwise the stored URL is not publicly deliverable.
        content_type = (getattr(file, 'content_type', '') or '').lower()
        if content_type.startswith('image/'):
            resource_type = 'image'
        elif content_type.startswith('video/'):
            resource_type = 'video'
        else:
            resource_type = 'raw'

        result = cloudinary.uploader.upload(file, folder=folder, resource_type=resource_type)
        return Response({
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'resource_type': resource_type,
        }, status=201)
