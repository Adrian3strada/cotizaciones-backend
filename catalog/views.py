from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from catalog.forms import CameraModelForm
from catalog.models import CameraModel


class CameraModelListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CameraModel
    template_name = "catalog/camera_list.html"
    permission_required = "catalog.view_cameramodel"


class CameraModelDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CameraModel
    template_name = "catalog/camera_detail.html"
    permission_required = "catalog.view_cameramodel"


class CameraModelCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CameraModel
    form_class = CameraModelForm
    template_name = "catalog/camera_form.html"
    permission_required = "catalog.add_cameramodel"


class CameraModelUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CameraModel
    form_class = CameraModelForm
    template_name = "catalog/camera_form.html"
    permission_required = "catalog.change_cameramodel"


class CameraModelDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = CameraModel
    template_name = "catalog/camera_confirm_delete.html"
    permission_required = "catalog.delete_cameramodel"
    success_url = reverse_lazy("catalog:list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                "No se puede eliminar el modelo porque está en cotizaciones. "
                "Desactívalo en su ficha si ya no lo usas.",
            )
            return redirect("catalog:detail", pk=self.object.pk)
