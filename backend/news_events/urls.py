from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NewsEventViewSet

router = DefaultRouter()
router.register('', NewsEventViewSet, basename='news-event')

urlpatterns = [path('', include(router.urls))]
