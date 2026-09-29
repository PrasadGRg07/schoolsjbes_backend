from django.contrib import admin
from .models import HomeHero


@admin.register(HomeHero)
class HomeHeroAdmin(admin.ModelAdmin):
    list_display = ['eyebrow', 'updated_at']

    def has_add_permission(self, request):
        # Singleton — the row is created by the API on first read.
        return not HomeHero.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
