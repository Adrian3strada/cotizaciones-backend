from django.contrib import admin
from quotes.models import Quote, QuoteItem

class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('quote_number', 'customer', 'status', 'special_discount_percent', 'total', 'valid_until')
    search_fields = ('quote_number', 'customer__name')
    list_filter = ('status', 'currency')
    inlines = [QuoteItemInline]

@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ('quote', 'camera_model', 'quantity', 'unit_price', 'discount_percent', 'line_subtotal')
    search_fields = ('quote__quote_number', 'camera_model__model_code')
