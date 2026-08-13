from django.contrib import admin
from .models import SchoolInfo


@admin.register(SchoolInfo)
class SchoolInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'short_name', 'tagline', 'established_year')}),
        ('Branding', {'fields': ('logo', 'logo_url', 'hero_image_url')}),
        ('Location', {'fields': ('address', 'city', 'district', 'province', 'country')}),
        ('Contact', {'fields': ('phone_primary', 'phone_secondary', 'email_primary', 'email_secondary')}),
        ('Online', {'fields': ('map_embed_url', 'facebook_url', 'youtube_url', 'twitter_url')}),
    )
    list_display = ['name', 'short_name', 'city', 'phone_primary', 'updated_at']

    def has_add_permission(self, request):
        return not SchoolInfo.objects.exists()
