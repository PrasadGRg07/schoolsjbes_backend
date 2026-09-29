from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import HomeHero
from .serializers import HomeHeroSerializer


class HomeHeroView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        obj, _ = HomeHero.objects.get_or_create(pk=1)
        return Response(HomeHeroSerializer(obj).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=401)
        obj, _ = HomeHero.objects.get_or_create(pk=1)
        serializer = HomeHeroSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
