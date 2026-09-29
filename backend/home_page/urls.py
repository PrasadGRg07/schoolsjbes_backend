from django.urls import path
from .views import HomeHeroView

urlpatterns = [
    path('hero/', HomeHeroView.as_view(), name='home_hero'),
]
