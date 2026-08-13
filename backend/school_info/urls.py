from django.urls import path
from .views import SchoolInfoView

urlpatterns = [
    path('', SchoolInfoView.as_view(), name='school_info'),
]
