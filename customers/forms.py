import re

from django import forms

from customers.models import Customer, CustomerContact

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "rfc",
            "website",
            "street_address",
            "neighborhood",
            "city",
            "postal_code",
            "phone",
            "mobile",
        ]

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value and "://" not in value:
            return "https://" + value
        return value


class CustomerContactForm(forms.ModelForm):
    class Meta:
        model = CustomerContact
        fields = [
            "customer",
            "full_name",
            "email",
            "mobile",
            "position",
            "is_primary",
        ]

    def clean_email(self):
        value = self.cleaned_data.get("email", "").strip()
        if value and not EMAIL_REGEX.match(value):
            raise forms.ValidationError("Ingresa un correo electrónico válido.")
        return value
