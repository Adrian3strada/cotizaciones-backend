from django.urls import path
from catalog import views
app_name = 'catalog'
urlpatterns = [path('', views.CameraModelListView.as_view(), name='list'), path('nuevo/', views.CameraModelCreateView.as_view(), name='create'), path('<int:pk>/', views.CameraModelDetailView.as_view(), name='detail'), path('<int:pk>/editar/', views.CameraModelUpdateView.as_view(), name='update'), path('<int:pk>/eliminar/', views.CameraModelDeleteView.as_view(), name='delete')]
