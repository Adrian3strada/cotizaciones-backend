from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from catalog.models import CameraModel
from customers.models import Customer, CustomerContact


class Quote(models.Model):
    STATUS_DRAFT = "DRAFT"
    STATUS_SENT = "SENT"
    STATUS_ACCEPTED = "ACCEPTED"
    STATUS_REJECTED = "REJECTED"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Borrador"),
        (STATUS_SENT, "Enviada"),
        (STATUS_ACCEPTED, "Aceptada"),
        (STATUS_REJECTED, "Rechazada"),
        (STATUS_EXPIRED, "Expirada"),
    ]

    CURRENCY_MXN = "MXN"
    CURRENCY_USD = "USD"
    CURRENCY_CHOICES = [
        (CURRENCY_MXN, "MXN"),
        (CURRENCY_USD, "USD"),
    ]

    quote_number = models.CharField("Número", max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        Customer, verbose_name="Cliente", on_delete=models.PROTECT, related_name="quotes"
    )
    contact = models.ForeignKey(
        CustomerContact,
        verbose_name="Contacto",
        on_delete=models.SET_NULL,
        related_name="quotes",
        null=True,
        blank=True,
    )
    sales_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Vendedor", on_delete=models.PROTECT
    )
    status = models.CharField(
        "Estatus", max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    issue_date = models.DateField("Fecha de emisión", default=timezone.localdate)
    valid_until = models.DateField("Vigencia")
    currency = models.CharField("Moneda", max_length=3, choices=CURRENCY_CHOICES)
    subtotal = models.DecimalField(
        "Subtotal", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    tax_rate = models.DecimalField(
        "IVA (%)", max_digits=5, decimal_places=2, default=Decimal("16.00")
    )
    tax_amount = models.DecimalField(
        "IVA", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(
        "Total", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.TextField("Notas", blank=True)
    terms = models.TextField("Términos", blank=True)
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.quote_number

    def clean(self) -> None:
        if self.valid_until is None:
            raise ValidationError({"valid_until": "La vigencia es obligatoria."})
        if self.issue_date and self.valid_until and self.valid_until <= self.issue_date:
            raise ValidationError(
                {"valid_until": "La vigencia debe ser posterior a la fecha de emisión."}
            )
        if self.status == self.STATUS_SENT and self.pk and not self.items.exists():
            raise ValidationError({"status": "No puedes enviar una cotización sin items."})
        if self.status == self.STATUS_SENT and not self.pk:
            # Prevent SENT on initial creation (no items yet).
            raise ValidationError({"status": "No puedes enviar una cotización sin items."})

    def save(self, *args, **kwargs):
        if self.valid_until and self.status != self.STATUS_ACCEPTED:
            if self.valid_until < timezone.localdate():
                self.status = self.STATUS_EXPIRED
        if self.quote_number:
            return super().save(*args, **kwargs)
        for _ in range(5):
            self.quote_number = self.generate_quote_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.quote_number = ""
                continue
        raise IntegrityError("No se pudo generar un número de cotización único.")

    def generate_quote_number(self) -> str:
        year = timezone.localdate().year
        prefix = f"SCP-{year}-"
        last_quote = (
            Quote.objects.filter(quote_number__startswith=prefix)
            .order_by("-quote_number")
            .first()
        )
        next_number = 1
        if last_quote:
            last_suffix = last_quote.quote_number.split("-")[-1]
            try:
                next_number = int(last_suffix) + 1
            except ValueError:
                next_number = 1
        return f"{prefix}{next_number:06d}"

    def recalculate_totals(self) -> None:
        items = self.items.all()
        subtotal = sum((item.line_subtotal or Decimal("0.00") for item in items), Decimal("0.00"))
        tax_rate = self.tax_rate or Decimal("0.00")
        try:
            tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        except InvalidOperation:
            tax_amount = Decimal("0.00")
        total = subtotal + tax_amount
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total = total
        Quote.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total=self.total,
        )


class QuoteItem(models.Model):
    quote = models.ForeignKey(
        Quote, verbose_name="Cotización", on_delete=models.CASCADE, related_name="items"
    )
    camera_model = models.ForeignKey(
        CameraModel, verbose_name="Modelo de cámara", on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField("Cantidad")
    unit_price = models.DecimalField("Precio unitario", max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(
        "Descuento", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    line_subtotal = models.DecimalField(
        "Subtotal línea", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    configuration_notes = models.TextField("Notas de configuración", blank=True)

    class Meta:
        verbose_name = "Item de cotización"
        verbose_name_plural = "Items de cotización"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.quote.quote_number} - {self.camera_model}"

    def clean(self) -> None:
        if self.quantity is None:
            return
        if self.quantity <= 0:
            raise ValidationError({"quantity": "La cantidad debe ser mayor que cero."})
        if self.unit_price is not None and self.unit_price < 0:
            raise ValidationError({"unit_price": "El precio no puede ser negativo."})
        if self.discount_amount is not None and self.discount_amount < 0:
            raise ValidationError({"discount_amount": "El descuento no puede ser negativo."})
        if self.quote_id and self.camera_model_id:
            quote_currency = self.quote.currency
            model_currency = self.camera_model.currency
            if quote_currency and model_currency and quote_currency != model_currency:
                raise ValidationError(
                    {
                        "camera_model": (
                            f"La moneda del modelo ({model_currency}) no coincide con "
                            f"la moneda de la cotización ({quote_currency})."
                        )
                    }
                )
        unit_price = self.unit_price or Decimal("0.00")
        max_discount = self.quantity * unit_price
        if self.discount_amount is not None and self.discount_amount > max_discount:
            raise ValidationError({"discount_amount": "El descuento no puede exceder el subtotal."})

    def save(self, *args, **kwargs):
        if self.quantity is None:
            self.line_subtotal = Decimal("0.00")
            return super().save(*args, **kwargs)
        if self.unit_price is None:
            self.unit_price = self.camera_model.base_price
        discount_amount = self.discount_amount or Decimal("0.00")
        line_subtotal = (self.unit_price * self.quantity) - discount_amount
        if line_subtotal < 0:
            line_subtotal = Decimal("0.00")
        self.line_subtotal = line_subtotal
        super().save(*args, **kwargs)
