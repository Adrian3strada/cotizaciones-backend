from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("usuarios/", views.UserListView.as_view(), name="list"),
    path("usuarios/nuevo/", views.UserCreateView.as_view(), name="create"),
    path("usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="update"),
    path("usuarios/<int:pk>/eliminar/", views.UserDeleteView.as_view(), name="delete"),
]
