from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, filters
from accounts.permissions import IsAdminOrReadOnly, PublishedOnlyMixin
from .models import Notice
from .serializers import NoticeSerializer


class NoticeViewSet(PublishedOnlyMixin, viewsets.ModelViewSet):
    public_filter = {'is_published': True}
    serializer_class = NoticeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'category']
    ordering_fields = ['published_date', 'is_important']

    def get_queryset(self):
        qs = Notice.objects.all()
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        qs = self.apply_published_only(qs)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        if self.request.query_params.get('popup') == 'true':
            today = timezone.now().date()
            qs = qs.filter(show_popup=True).filter(
                Q(popup_expires_at__isnull=True) | Q(popup_expires_at__gte=today)
            )
        return qs
