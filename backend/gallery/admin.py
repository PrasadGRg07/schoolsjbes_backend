from django.contrib import admin
from .models import Album, GalleryPhoto


class GalleryPhotoInline(admin.TabularInline):
    model = GalleryPhoto
    extra = 1
    fields = ['image_url', 'caption', 'order']


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'is_published', 'order']
    list_filter = ['is_published']
    list_editable = ['is_published', 'order']
    search_fields = ['title', 'description']
    date_hierarchy = 'date'
    inlines = [GalleryPhotoInline]


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ['album', 'caption', 'order', 'uploaded_at']
    list_filter = ['album']
    search_fields = ['caption']
