import re
from django import forms
from django.core.validators import URLValidator
from customers.models import Customer, CustomerContact
EMAIL_REGEX = re.compile('^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')

class CustomerForm(forms.ModelForm):

    class Meta:
        model = Customer
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'}), 'country_code': forms.TextInput(attrs={'maxlength': 2, 'class': 'form-control', 'placeholder': 'MX'}), 'rfc': forms.TextInput(attrs={'class': 'form-control'}), 'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}), 'street_address': forms.TextInput(attrs={'class': 'form-control'}), 'neighborhood': forms.TextInput(attrs={'class': 'form-control'}), 'city': forms.TextInput(attrs={'class': 'form-control'}), 'postal_code': forms.TextInput(attrs={'class': 'form-control'}), 'phone': forms.TextInput(attrs={'class': 'form-control'})}
        fields = ['name', 'country_code', 'rfc', 'website', 'street_address', 'neighborhood', 'city', 'postal_code', 'phone']

    def clean_website(self):
        value = self.cleaned_data.get('website', '').strip()
        if not value:
            return value
        if '://' not in value:
            value = 'https://' + value
        validator = URLValidator()
        try:
            validator(value)
        except Exception:
            raise forms.ValidationError('Ingresa una URL válida.')
        return value

class CustomerContactForm(forms.ModelForm):

    class Meta:
        model = CustomerContact
        fields = ['customer', 'full_name', 'email', 'mobile', 'position', 'is_primary']
        widgets = {'customer': forms.Select(attrs={'class': 'form-control'}), 'full_name': forms.TextInput(attrs={'class': 'form-control'}), 'email': forms.EmailInput(attrs={'class': 'form-control'}), 'mobile': forms.TextInput(attrs={'class': 'form-control'}), 'position': forms.TextInput(attrs={'class': 'form-control'}), 'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input app-form-check-input'})}

    def clean_email(self):
        value = self.cleaned_data.get('email', '').strip()
        if value and (not EMAIL_REGEX.match(value)):
            raise forms.ValidationError('Ingresa un correo electrónico válido.')
        return value
