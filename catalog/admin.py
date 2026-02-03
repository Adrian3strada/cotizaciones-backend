from django.contrib import admin

from catalog.models import CameraModel


@admin.register(CameraModel)
class CameraModelAdmin(admin.ModelAdmin):
    list_display = ("model_code", "brand", "name", "base_price", "currency", "is_active")
    search_fields = ("model_code", "name", "brand")
    list_filter = ("currency", "is_active")
