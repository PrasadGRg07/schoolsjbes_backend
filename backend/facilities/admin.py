from django.contrib import admin
from .models import Facility, FacilityImage


class FacilityImageInline(admin.TabularInline):
    model = FacilityImage
    extra = 1
    fields = ['image_url', 'caption', 'order']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order', 'is_active']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    search_fields = ['name']
    inlines = [FacilityImageInline]


@admin.register(FacilityImage)
class FacilityImageAdmin(admin.ModelAdmin):
    list_display = ['facility', 'caption', 'order']
    list_filter = ['facility']
