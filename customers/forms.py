from django import forms

from customers.models import Customer, CustomerContact


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
