from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FacilityViewSet, FacilityImageViewSet

router = DefaultRouter()
router.register('', FacilityViewSet, basename='facility')
router.register('images', FacilityImageViewSet, basename='facility-image')

urlpatterns = [path('', include(router.urls))]
