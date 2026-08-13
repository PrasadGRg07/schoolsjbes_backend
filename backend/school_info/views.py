from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import SchoolInfo
from .serializers import SchoolInfoSerializer


class SchoolInfoView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        obj = SchoolInfo.get_instance()
        return Response(SchoolInfoSerializer(obj).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        obj = SchoolInfo.get_instance()
        serializer = SchoolInfoSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
