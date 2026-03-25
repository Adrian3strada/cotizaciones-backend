from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django import forms
from django.forms.models import BaseInlineFormSet
from django.forms import inlineformset_factory
from django.utils import timezone
from customers.models import CustomerContact
from quotes.models import Quote, QuoteItem

class QuoteForm(forms.ModelForm):

    class Meta:
        model = Quote
        fields = ['customer', 'contact', 'status', 'currency', 'usd_mxn_rate', 'issue_date', 'valid_until', 'tax_rate', 'special_discount_percent', 'cableado', 'cableado_monto', 'instalacion', 'instalacion_monto', 'poe', 'poe_monto', 'notes', 'terms']
        widgets = {'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), 'valid_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), 'usd_mxn_rate': forms.NumberInput(attrs={'min': 0, 'step': '0.0001', 'class': 'form-control', 'placeholder': 'Ej. 20.00'}), 'special_discount_percent': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'placeholder': '0'}), 'poe_monto': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': '0'}), 'terms': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valid_until'].required = False
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields['issue_date'].initial = today
            self.fields['valid_until'].initial = today + timedelta(days=30)
            self.fields['terms'].initial = 'Entrega 10-15 días hábiles. Pago 50% anticipo, 50% contra entrega. Garantía 1 año.'
        self.fields['special_discount_percent'].required = False
        self.fields['usd_mxn_rate'].required = False
        self.fields['cableado_monto'].required = False
        self.fields['instalacion_monto'].required = False
        self.fields['poe_monto'].required = False
        self.fields['terms'].required = False
        self.fields['contact'].queryset = CustomerContact.objects.none()
        if self.instance and self.instance.pk and self.instance.customer_id:
            self.fields['contact'].queryset = CustomerContact.objects.filter(customer_id=self.instance.customer_id).order_by('full_name')
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
            except (TypeError, ValueError):
                customer_id = None
            if customer_id:
                self.fields['contact'].queryset = CustomerContact.objects.filter(customer_id=customer_id).order_by('full_name')

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        contact = cleaned_data.get('contact')
        issue_date = cleaned_data.get('issue_date')
        valid_until = cleaned_data.get('valid_until')
        if contact and customer and (contact.customer_id != customer.id):
            self.add_error('contact', 'El contacto debe pertenecer al cliente seleccionado.')
        if issue_date and valid_until and (issue_date > valid_until):
            self.add_error('valid_until', 'La vigencia debe ser posterior o igual a la fecha de emisión.')
        if valid_until and valid_until < timezone.localdate():
            self.add_error('valid_until', 'La vigencia no puede ser anterior a hoy. La cotización estaría expirada.')
        currency = cleaned_data.get('currency')
        rate = cleaned_data.get('usd_mxn_rate')
        if currency == Quote.CURRENCY_MXN:
            if rate is None or rate <= 0:
                self.add_error('usd_mxn_rate', 'Indica el tipo de cambio (MXN por 1 USD) para cotizar en pesos.')
        else:
            cleaned_data['usd_mxn_rate'] = None
        return cleaned_data

class QuoteItemForm(forms.ModelForm):

    class Meta:
        model = QuoteItem
        fields = ['camera_model', 'quantity', 'unit_price', 'discount_percent']
        widgets = {'unit_price': forms.NumberInput(attrs={'readonly': True, 'step': '0.01', 'class': 'form-control input-readonly input-unit-price'}), 'discount_percent': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'class': 'form-control input-number-narrow'}), 'quantity': forms.NumberInput(attrs={'min': 1, 'class': 'form-control input-number-narrow'})}

    def __init__(self, *args, quote_currency=None, usd_mxn_rate=None, **kwargs):
        self._quote_currency = quote_currency
        self._usd_mxn_rate = usd_mxn_rate
        super().__init__(*args, **kwargs)
        self.fields['unit_price'].required = False
        self.fields['discount_percent'].required = False
        if self.instance and self.instance.pk and self.instance.camera_model_id:
            q = self.instance.quote
            self.fields['unit_price'].initial = Quote.unit_price_from_catalog_base(self.instance.camera_model.base_price, q.currency if q else self._quote_currency or '', getattr(q, 'usd_mxn_rate', None) if q else self._usd_mxn_rate)

    def _coerce_rate(self):
        if self._usd_mxn_rate is None:
            return None
        if isinstance(self._usd_mxn_rate, Decimal):
            return self._usd_mxn_rate
        try:
            return Decimal(str(self._usd_mxn_rate))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def clean(self):
        cleaned_data = super().clean()
        camera_model = cleaned_data.get('camera_model')
        if camera_model:
            qc = (self._quote_currency or '').strip()
            rate = self._coerce_rate()
            q = getattr(self.instance, 'quote', None)
            if q is not None and getattr(q, 'pk', None):
                qc = q.currency
                rate = q.usd_mxn_rate
            cleaned_data['unit_price'] = Quote.unit_price_from_catalog_base(camera_model.base_price, qc, rate)
        return cleaned_data

class BaseQuoteItemFormSet(BaseInlineFormSet):

    def __init__(self, *args, quote_currency=None, usd_mxn_rate=None, **kwargs):
        self.quote_currency = quote_currency
        self.usd_mxn_rate = usd_mxn_rate
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['quote_currency'] = self.quote_currency
        kwargs['usd_mxn_rate'] = self.usd_mxn_rate
        return kwargs
QuoteItemFormSet = inlineformset_factory(Quote, QuoteItem, form=QuoteItemForm, formset=BaseQuoteItemFormSet, extra=1, can_delete=True)
