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
            "currency",
            "tax_rate",
            "special_discount_percent",
            "cableado",
            "cableado_monto",
            "instalacion",
            "instalacion_monto",
            "inyector_poe",
            "inyector_poe_monto",
            "poe",
            "poe_monto",
            "notes",
        ]
        widgets = {
            "special_discount_percent": forms.NumberInput(
                attrs={"min": 0, "max": 100, "step": "0.01", "placeholder": "0"}
            ),
            "cableado_monto": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "0"}),
            "instalacion_monto": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "0"}),
            "inyector_poe_monto": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "0"}),
            "poe_monto": forms.NumberInput(attrs={"min": 0, "step": "0.01", "placeholder": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["special_discount_percent"].required = False
        self.fields["cableado_monto"].required = False
        self.fields["instalacion_monto"].required = False
        self.fields["inyector_poe_monto"].required = False
        self.fields["poe_monto"].required = False
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
            "discount_percent",
        ]
        widgets = {
            "unit_price": forms.NumberInput(
                attrs={
                    "readonly": True,
                    "step": "0.01",
                    "class": "form-control input-readonly",
                }
            ),
            "discount_percent": forms.NumberInput(
                attrs={"min": 0, "max": 100, "step": "0.01", "class": "form-control input-number-narrow"}
            ),
            "quantity": forms.NumberInput(
                attrs={"min": 1, "class": "form-control input-number-narrow"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit_price"].required = False
        self.fields["discount_percent"].required = False
        if self.instance and self.instance.pk and self.instance.camera_model_id:
            self.fields["unit_price"].initial = self.instance.camera_model.base_price

    def clean(self):
        cleaned_data = super().clean()
        camera_model = cleaned_data.get("camera_model")
        if camera_model:
            cleaned_data["unit_price"] = camera_model.base_price
        return cleaned_data


QuoteItemFormSet = inlineformset_factory(
    Quote,
    QuoteItem,
    form=QuoteItemForm,
    extra=1,
    can_delete=True,
)
