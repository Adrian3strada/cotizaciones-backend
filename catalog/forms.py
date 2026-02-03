from django import forms

from catalog.models import CameraModel


class CameraModelForm(forms.ModelForm):
    class Meta:
        model = CameraModel
        fields = [
            "brand",
            "model_code",
            "name",
            "description",
            "datasheet_file",
            "base_price",
            "currency",
            "is_active",
        ]
