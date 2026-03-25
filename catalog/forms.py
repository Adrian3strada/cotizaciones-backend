from django import forms
from catalog.models import CameraModel

class CameraModelForm(forms.ModelForm):

    class Meta:
        model = CameraModel
        fields = ['brand', 'model_code', 'name', 'description', 'datasheet_file', 'base_price', 'is_active']
        widgets = {'brand': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'organization'}), 'model_code': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}), 'name': forms.TextInput(attrs={'class': 'form-control'}), 'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), 'datasheet_file': forms.ClearableFileInput(attrs={'class': 'form-control catalog-file-input'}), 'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'inputmode': 'decimal'}), 'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input catalog-active-cb'})}

    def clean_base_price(self):
        base_price = self.cleaned_data.get('base_price')
        if base_price is not None and base_price < 0:
            raise forms.ValidationError('El precio base no puede ser negativo.')
        return base_price
