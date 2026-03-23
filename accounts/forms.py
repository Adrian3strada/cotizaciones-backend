from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class UserBaseForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Group.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email", "is_active", "groups"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input app-form-check-input"}),
        }


class UserCreateForm(UserBaseForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    class Meta(UserBaseForm.Meta):
        fields = UserBaseForm.Meta.fields + ["password1", "password2"]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif len(password1) < 8:
                self.add_error("password1", "La contraseña debe tener al menos 8 caracteres.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserUpdateForm(UserBaseForm):
    password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        required=False,
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        required=False,
    )

    class Meta(UserBaseForm.Meta):
        fields = UserBaseForm.Meta.fields + ["password1", "password2"]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif password1 and len(password1) < 8:
                self.add_error("password1", "La contraseña debe tener al menos 8 caracteres.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password1 = self.cleaned_data.get("password1")
        if password1:
            user.set_password(password1)
        if commit:
            user.save()
            self.save_m2m()
        return user
