from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TextSlideViewSet, ImageSlideViewSet

router = DefaultRouter()
router.register('text', TextSlideViewSet, basename='text-slide')
router.register('images', ImageSlideViewSet, basename='image-slide')

urlpatterns = [path('', include(router.urls))]
