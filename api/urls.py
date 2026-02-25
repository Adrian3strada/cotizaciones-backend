from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CameraModelViewSet, CustomerViewSet, QuoteViewSet

router = DefaultRouter()
router.register(r"catalog", CameraModelViewSet, basename="api-catalog")
router.register(r"customers", CustomerViewSet, basename="api-customers")
router.register(r"quotes", QuoteViewSet, basename="api-quotes")

urlpatterns = [
    path("", include(router.urls)),
]
