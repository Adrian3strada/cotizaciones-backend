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

    def clean_base_price(self):
        base_price = self.cleaned_data.get("base_price")
        if base_price is not None and base_price < 0:
            raise forms.ValidationError("El precio base no puede ser negativo.")
        return base_price
