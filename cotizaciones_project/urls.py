"""
URL configuration for cotizaciones_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def logout_view(request):
    logout(request)
    return redirect('login')


def handler404(request, exception):
    from django.shortcuts import render
    return render(request, "404.html", status=404)


def handler500(request):
    from django.shortcuts import render
    return render(request, "500.html", status=500)


def _openapi_view(view_cls, **initkwargs):
    """En producción, Swagger/ReDoc/schema solo para staff salvo OPENAPI_PUBLIC=true."""
    view = view_cls.as_view(**initkwargs)
    if settings.DEBUG or os.environ.get("OPENAPI_PUBLIC", "").lower() in ("1", "true", "yes"):
        return view
    return staff_member_required(view)


urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', TemplateView.as_view(
        template_name='registration/password_reset_info.html',
    ), name='password_reset'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path("api/schema/", _openapi_view(SpectacularAPIView), name="schema"),
    path(
        "api/schema/swagger-ui/",
        _openapi_view(SpectacularSwaggerView, url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        _openapi_view(SpectacularRedocView, url_name="schema"),
        name="redoc",
    ),
    path('', include('quotes.urls')),
    path('clientes/', include('customers.urls')),
    path('catalogo/', include('catalog.urls')),
    path('', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
