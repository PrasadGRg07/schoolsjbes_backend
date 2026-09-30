"""
Root URL Configuration for SJBEBS School Website API
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenBlacklistView,
)
from accounts.views import AdminTokenObtainPairView

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # Auth. Each door admits only its own role, so a teacher cannot end up
    # holding an admin session by typing the wrong form.
    path('api/auth/token/', AdminTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/auth/', include('accounts.urls')),
    path('api/teacher/', include('accounts.teacher_urls')),

    # Public content modules
    path('api/school-info/', include('school_info.urls')),
    path('api/home/', include('home_page.urls')),
    path('api/about/', include('about.urls')),
    path('api/teachers/', include('teachers.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/admissions/', include('admissions.urls')),
    path('api/facilities/', include('facilities.urls')),
    path('api/gallery/', include('gallery.urls')),
    path('api/news/', include('news_events.urls')),
    path('api/notices/', include('notices.urls')),
    path('api/contact/', include('contact.urls')),
    path('api/settings/', include('site_settings.urls')),
    path('api/carousel/', include('carousel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
