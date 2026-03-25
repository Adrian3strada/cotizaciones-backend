from django.urls import include, path
from rest_framework.authtoken import views as authtoken_views
from rest_framework.routers import DefaultRouter
from .views import CameraModelViewSet, CustomerViewSet, QuoteViewSet
router = DefaultRouter()
router.register('catalog', CameraModelViewSet, basename='api-catalog')
router.register('customers', CustomerViewSet, basename='api-customers')
router.register('quotes', QuoteViewSet, basename='api-quotes')
urlpatterns = [path('auth-token/', authtoken_views.obtain_auth_token), path('', include(router.urls))]
