from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import AdminProfileSerializer, ChangePasswordSerializer
import cloudinary.uploader

User = get_user_model()


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

        result = cloudinary.uploader.upload(file, folder=folder)
        return Response({
            'url': result['secure_url'],
            'public_id': result['public_id'],
        }, status=201)
