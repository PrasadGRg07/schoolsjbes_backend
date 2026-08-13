from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import NewsEvent
from .serializers import NewsEventSerializer, NewsEventListSerializer


class NewsEventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['created_at', 'event_date']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return NewsEventListSerializer
        return NewsEventSerializer

    def get_queryset(self):
        qs = NewsEvent.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        type_filter = self.request.query_params.get('type')
        if type_filter:
            qs = qs.filter(type=type_filter)
        return qs
