from django.contrib import admin
from .models import TextSlide, ImageSlide


@admin.register(TextSlide)
class TextSlideAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_enabled', 'order']
    list_filter = ['is_enabled']
    list_editable = ['is_enabled', 'order']
    search_fields = ['title', 'subtitle']


@admin.register(ImageSlide)
class ImageSlideAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'title', 'is_enabled', 'order']
    list_filter = ['is_enabled']
    list_editable = ['is_enabled', 'order']
    search_fields = ['title', 'caption']
