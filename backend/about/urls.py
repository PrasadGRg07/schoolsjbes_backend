from django.urls import path
from .views import PrincipalMessageView, SchoolHistoryView

urlpatterns = [
    path('principal/', PrincipalMessageView.as_view(), name='principal_message'),
    path('history/', SchoolHistoryView.as_view(), name='school_history'),
]
