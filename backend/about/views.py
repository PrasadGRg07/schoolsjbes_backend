from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsAdminOrReadOnly
from .models import PrincipalMessage, SchoolHistory
from .serializers import PrincipalMessageSerializer, SchoolHistorySerializer


class PrincipalMessageView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        obj, _ = PrincipalMessage.objects.get_or_create(pk=1, defaults={
            'principal_name': 'Principal Name',
            'message': 'Welcome message from the principal.'
        })
        return Response(PrincipalMessageSerializer(obj).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        obj, _ = PrincipalMessage.objects.get_or_create(pk=1)
        serializer = PrincipalMessageSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class SchoolHistoryView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        obj, _ = SchoolHistory.objects.get_or_create(pk=1)
        return Response(SchoolHistorySerializer(obj).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        obj, _ = SchoolHistory.objects.get_or_create(pk=1)
        serializer = SchoolHistorySerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
