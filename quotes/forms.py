from django import forms
from django.forms import inlineformset_factory

from customers.models import CustomerContact
from quotes.models import Quote, QuoteItem


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = [
            "customer",
            "contact",
            "status",
            "valid_until",
            "currency",
            "tax_rate",
            "notes",
            "terms",
        ]
        widgets = {
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valid_until"].required = True
        self.fields["contact"].queryset = CustomerContact.objects.none()
        if self.instance and self.instance.pk and self.instance.customer_id:
            self.fields["contact"].queryset = CustomerContact.objects.filter(
                customer_id=self.instance.customer_id
            ).order_by("full_name")
        if "customer" in self.data:
            try:
                customer_id = int(self.data.get("customer"))
            except (TypeError, ValueError):
                customer_id = None
            if customer_id:
                self.fields["contact"].queryset = CustomerContact.objects.filter(
                    customer_id=customer_id
                ).order_by("full_name")

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get("customer")
        contact = cleaned_data.get("contact")
        if contact and customer and contact.customer_id != customer.id:
            self.add_error("contact", "El contacto debe pertenecer al cliente seleccionado.")
        return cleaned_data


class QuoteItemForm(forms.ModelForm):
    class Meta:
        model = QuoteItem
        fields = [
            "camera_model",
            "quantity",
            "unit_price",
            "discount_amount",
            "configuration_notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit_price"].required = False


QuoteItemFormSet = inlineformset_factory(
    Quote,
    QuoteItem,
    form=QuoteItemForm,
    extra=1,
    can_delete=True,
)
