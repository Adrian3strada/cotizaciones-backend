from django import forms

from customers.models import Customer, CustomerContact


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "website",
            "street_address",
            "neighborhood",
            "postal_code",
            "phone",
        ]


class CustomerContactForm(forms.ModelForm):
    class Meta:
        model = CustomerContact
        fields = [
            "customer",
            "full_name",
            "email",
            "phone",
            "mobile",
            "position",
            "is_primary",
        ]
