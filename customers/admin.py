from django.contrib import admin
from customers.models import Customer, CustomerContact

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_code', 'rfc', 'is_active', 'created_at')
    search_fields = ('name', 'rfc')
    list_filter = ('is_active',)

@admin.register(CustomerContact)
class CustomerContactAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'customer', 'email', 'phone', 'mobile', 'is_primary')
    search_fields = ('full_name', 'email', 'phone', 'customer__name')
    list_filter = ('is_primary',)
