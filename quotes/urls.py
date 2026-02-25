from django.urls import path

from quotes import views

app_name = "quotes"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("cotizaciones/", views.QuoteListView.as_view(), name="list"),
    path("cotizaciones/exportar/", views.quote_list_export, name="list_export"),
    path("cotizaciones/nueva/", views.quote_create, name="create"),
    path("cotizaciones/<int:pk>/", views.QuoteDetailView.as_view(), name="detail"),
    path("cotizaciones/<int:pk>/editar/", views.quote_update, name="update"),
    path("cotizaciones/<int:pk>/enviar/", views.quote_send, name="send"),
    path("cotizaciones/<int:pk>/estado/<str:status>/", views.quote_mark, name="mark"),
    path("cotizaciones/<int:pk>/duplicar/", views.quote_duplicate, name="duplicate"),
    path("cotizaciones/<int:pk>/pdf/", views.quote_pdf, name="pdf"),
    path("reportes/", views.report_view, name="report"),
    path("reportes/exportar/", views.report_export, name="report_export"),
]
