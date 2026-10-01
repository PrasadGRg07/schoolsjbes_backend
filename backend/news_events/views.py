from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, filters
from accounts.permissions import IsAdminOrReadOnly, PublishedOnlyMixin
from .models import NewsEvent
from .serializers import NewsEventSerializer, NewsEventListSerializer


class NewsEventViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_published': True}
    permission_classes = [IsAdminOrReadOnly]
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
        qs = self.apply_published_only(qs)
        type_filter = self.request.query_params.get('type')
        if type_filter:
            qs = qs.filter(type=type_filter)
        if self.request.query_params.get('popup') == 'true':
            today = timezone.now().date()
            qs = qs.filter(show_popup=True).filter(
                Q(popup_expires_at__isnull=True) | Q(popup_expires_at__gte=today)
            )
        return qs
