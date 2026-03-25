from rest_framework import serializers
from catalog.models import CameraModel
from customers.models import Customer, CustomerContact
from quotes.models import Quote, QuoteItem

class CameraModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = CameraModel
        fields = ['id', 'brand', 'model_code', 'name', 'description', 'base_price', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class CustomerContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerContact
        fields = ['id', 'full_name', 'email', 'phone', 'mobile', 'position', 'is_primary']

class CustomerSerializer(serializers.ModelSerializer):
    contacts = CustomerContactSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'name', 'country_code', 'rfc', 'website', 'street_address', 'neighborhood', 'city', 'postal_code', 'phone', 'mobile', 'billing_address', 'shipping_address', 'notes', 'is_active', 'contacts', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class QuoteItemSerializer(serializers.ModelSerializer):
    camera_model_code = serializers.CharField(source='camera_model.model_code', read_only=True)
    camera_model_name = serializers.CharField(source='camera_model.name', read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'camera_model', 'camera_model_code', 'camera_model_name', 'quantity', 'unit_price', 'discount_percent', 'line_subtotal', 'group_name', 'order_in_group']

class QuoteListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sales_user_name = serializers.CharField(source='sales_user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Quote
        fields = ['id', 'quote_number', 'customer', 'customer_name', 'sales_user', 'sales_user_name', 'status', 'status_display', 'issue_date', 'valid_until', 'currency', 'usd_mxn_rate', 'subtotal', 'total', 'created_at']

class QuoteDetailSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    contact_name = serializers.SerializerMethodField()

    def get_contact_name(self, obj):
        return obj.contact.full_name if obj.contact else None
    sales_user_name = serializers.CharField(source='sales_user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Quote
        fields = ['id', 'quote_number', 'customer', 'customer_name', 'contact', 'contact_name', 'sales_user', 'sales_user_name', 'status', 'status_display', 'issue_date', 'valid_until', 'currency', 'usd_mxn_rate', 'subtotal', 'special_discount_percent', 'special_discount_amount', 'tax_rate', 'tax_amount', 'total', 'cableado', 'cableado_monto', 'instalacion', 'instalacion_monto', 'poe', 'poe_monto', 'notes', 'terms', 'items', 'created_at', 'updated_at']
