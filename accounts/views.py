from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.forms import UserCreateForm, UserUpdateForm
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileView(LoginRequiredMixin, TemplateView):
    """Página de perfil del usuario actual."""
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_user"] = self.request.user
        return context


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    permission_required = "auth.view_user"
    paginate_by = 20
    ordering = ["username"]


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    permission_required = "auth.add_user"
    success_url = reverse_lazy("accounts:list")


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    permission_required = "auth.change_user"
    success_url = reverse_lazy("accounts:list")


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/user_confirm_delete.html"
    permission_required = "auth.delete_user"
    success_url = reverse_lazy("accounts:list")
