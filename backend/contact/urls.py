from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactSubmitView, ContactMessageAdminViewSet

router = DefaultRouter()
router.register('messages', ContactMessageAdminViewSet, basename='contact-msg')

urlpatterns = [
    path('', ContactSubmitView.as_view(), name='contact_submit'),
    path('admin/', include(router.urls)),
]
