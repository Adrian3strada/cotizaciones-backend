from django.urls import path
from customers import views
app_name = 'customers'
urlpatterns = [path('', views.CustomerListView.as_view(), name='list'), path('nuevo/', views.CustomerCreateView.as_view(), name='create'), path('<int:pk>/', views.CustomerDetailView.as_view(), name='detail'), path('<int:pk>/editar/', views.CustomerUpdateView.as_view(), name='update'), path('<int:pk>/eliminar/', views.CustomerDeleteView.as_view(), name='delete'), path('contactos/<int:pk>/', views.customer_contacts, name='contacts'), path('contactos/nuevo/', views.CustomerContactCreateView.as_view(), name='contact_create'), path('contactos/<int:pk>/editar/', views.CustomerContactUpdateView.as_view(), name='contact_update')]
