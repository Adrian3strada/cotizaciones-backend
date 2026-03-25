from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import CameraModel
from customers.models import Customer
from quotes.access import user_sees_only_own_quotes
from quotes.models import Quote
from .serializers import CameraModelSerializer, CustomerSerializer, QuoteDetailSerializer, QuoteListSerializer

class CameraModelViewSet(viewsets.ModelViewSet):
    queryset = CameraModel.objects.filter(is_active=True).order_by('model_code')
    serializer_class = CameraModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['brand']
    search_fields = ['model_code', 'name', 'brand']
    ordering_fields = ['model_code', 'name', 'base_price', 'created_at']

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True).order_by('name')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'rfc', 'city']
    ordering_fields = ['name', 'created_at']

class QuoteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Quote.objects.select_related('customer', 'contact', 'sales_user').prefetch_related('items')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'currency', 'customer', 'sales_user']
    search_fields = ['quote_number', 'customer__name']
    ordering_fields = ['quote_number', 'issue_date', 'valid_until', 'total', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        if user_sees_only_own_quotes(self.request.user):
            qs = qs.filter(sales_user=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuoteDetailSerializer
        return QuoteListSerializer
