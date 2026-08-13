from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from .models import AdmissionInfo, AdmissionApplication
from .serializers import AdmissionInfoSerializer, AdmissionApplicationSerializer, AdmissionApplicationAdminSerializer


class AdmissionInfoView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        obj, _ = AdmissionInfo.objects.get_or_create(pk=1)
        return Response(AdmissionInfoSerializer(obj).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        obj, _ = AdmissionInfo.objects.get_or_create(pk=1)
        serializer = AdmissionInfoSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class AdmissionApplicationView(APIView):
    """Public: POST to apply. Admin: GET all applications."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdmissionApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Application submitted successfully.'}, status=201)
        return Response(serializer.errors, status=400)


class AdmissionApplicationAdminViewSet(viewsets.ModelViewSet):
    queryset = AdmissionApplication.objects.all()
    serializer_class = AdmissionApplicationAdminSerializer
    permission_classes = [IsAuthenticated]
