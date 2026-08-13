from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlbumViewSet, GalleryPhotoViewSet

router = DefaultRouter()
router.register('albums', AlbumViewSet, basename='album')
router.register('photos', GalleryPhotoViewSet, basename='photo')

urlpatterns = [path('', include(router.urls))]
