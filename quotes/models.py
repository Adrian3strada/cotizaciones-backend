from __future__ import annotations

from datetime import timedelta
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
    special_discount_percent = models.DecimalField(
        "Descuento especial (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Porcentaje de descuento especial aplicado al total de productos (todos los clientes).",
    )
    special_discount_amount = models.DecimalField(
        "Descuento especial (monto)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
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
    # Servicios opcionales
    cableado = models.BooleanField("Cableado", default=False)
    cableado_monto = models.DecimalField(
        "Cableado (monto)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    instalacion = models.BooleanField("Instalación", default=False)
    instalacion_monto = models.DecimalField(
        "Instalación (monto)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    inyector_poe = models.BooleanField("Inyector PoE", default=False)
    inyector_poe_monto = models.DecimalField(
        "Inyector PoE (monto)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    poe = models.BooleanField("PoE", default=False)
    poe_monto = models.DecimalField(
        "PoE (monto)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    notes = models.TextField("Observaciones", blank=True)
    terms = models.TextField(
        "Términos",
        blank=True,
        default="Entrega 10-15 días hábiles. Pago 50% anticipo, 50% contra entrega. Garantía 1 año.",
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sales_user", "status"]),
            models.Index(fields=["issue_date"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self) -> str:
        return self.quote_number

    def clean(self) -> None:
        if self.issue_date and not self.valid_until:
            self.valid_until = self.issue_date + timedelta(days=30)
        if self.status == self.STATUS_SENT and self.pk and not self.items.exists():
            raise ValidationError({"status": "No puedes enviar una cotización sin items."})
        if self.status == self.STATUS_SENT and not self.pk:
            # Prevent SENT on initial creation (no items yet).
            raise ValidationError({"status": "No puedes enviar una cotización sin items."})
        discount_pct = getattr(self, "special_discount_percent", None)
        if discount_pct is not None and (discount_pct < 0 or discount_pct > 100):
            raise ValidationError(
                {"special_discount_percent": "El descuento especial debe ser entre 0 y 100%."}
            )

    def save(self, *args, **kwargs):
        if self.issue_date and not self.valid_until:
            self.valid_until = self.issue_date + timedelta(days=30)
        if self.valid_until and self.status != self.STATUS_ACCEPTED:
            if self.valid_until < timezone.localdate():
                self.status = self.STATUS_EXPIRED
        if self.quote_number:
            return super().save(*args, **kwargs)
        for _ in range(5):
            try:
                with transaction.atomic():
                    self.quote_number = self.generate_quote_number()
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
            .select_for_update()
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

    @property
    def products_total_after_discount(self) -> Decimal:
        """Total de productos después del descuento (sin opcionales)."""
        st = self.subtotal or Decimal("0.00")
        disc = getattr(self, "special_discount_amount", None) or Decimal("0.00")
        return (st - disc).quantize(Decimal("0.01")) if (st - disc) >= 0 else Decimal("0.00")

    @property
    def subtotal_after_discount(self) -> Decimal:
        """Subtotal total después de descuento (productos + opcionales, base para IVA)."""
        if self.total is not None and self.tax_amount is not None:
            return (self.total - self.tax_amount).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @property
    def base_before_discount(self) -> Decimal:
        """Subtotal productos (antes de descuento)."""
        return self.subtotal or Decimal("0.00")

    def get_optional_services_total(self) -> Decimal:
        """Suma de los montos de servicios opcionales incluidos."""
        total = Decimal("0.00")
        m = getattr(self, "cableado_monto", None) or Decimal("0.00")
        if getattr(self, "cableado", False) and m > 0:
            total += m
        m = getattr(self, "instalacion_monto", None) or Decimal("0.00")
        if getattr(self, "instalacion", False) and m > 0:
            total += m
        m = getattr(self, "inyector_poe_monto", None) or Decimal("0.00")
        if getattr(self, "inyector_poe", False) and m > 0:
            total += m
        m = getattr(self, "poe_monto", None) or Decimal("0.00")
        if getattr(self, "poe", False) and m > 0:
            total += m
        return total

    def get_grouped_items(self) -> list[tuple[str | None, list["QuoteItem"]]]:
        """Items agrupados por group_name (igual que en el PDF). Retorna [(group_name, [items]), ...]."""
        items = list(self.items.select_related("camera_model").order_by("id"))
        groups: list[tuple[str | None, list[QuoteItem]]] = []
        current_group: tuple[str, list[QuoteItem]] | None = None
        for item in items:
            gn = (item.group_name or "").strip()
            if gn:
                if current_group is None or current_group[0] != gn:
                    current_group = (gn, [])
                    groups.append(current_group)
                current_group[1].append(item)
            else:
                current_group = None
                groups.append((None, [item]))
        # Ordenar items dentro de cada grupo
        result = []
        for gn, grp_items in groups:
            if gn:
                grp_items = sorted(grp_items, key=lambda x: (x.order_in_group, x.id))
            result.append((gn, grp_items))
        return result

    def get_optional_rows(self) -> list[dict]:
        """Lista de filas opcionales con partida consecutiva (sigue a los ítems de productos)."""
        base_partida = self.items.count()
        rows = []
        if getattr(self, "cableado", False) or (getattr(self, "cableado_monto", None) or 0) > 0:
            rows.append({
                "partida": base_partida + len(rows) + 1,
                "desc": "Cableado",
                "monto": getattr(self, "cableado_monto", None) or Decimal("0.00"),
            })
        if getattr(self, "instalacion", False) or (getattr(self, "instalacion_monto", None) or 0) > 0:
            rows.append({
                "partida": base_partida + len(rows) + 1,
                "desc": "Instalación",
                "monto": getattr(self, "instalacion_monto", None) or Decimal("0.00"),
            })
        if getattr(self, "inyector_poe", False) or (getattr(self, "inyector_poe_monto", None) or 0) > 0:
            rows.append({
                "partida": base_partida + len(rows) + 1,
                "desc": "Inyector PoE",
                "monto": getattr(self, "inyector_poe_monto", None) or Decimal("0.00"),
            })
        if getattr(self, "poe", False) or (getattr(self, "poe_monto", None) or 0) > 0:
            rows.append({
                "partida": base_partida + len(rows) + 1,
                "desc": "PoE",
                "monto": getattr(self, "poe_monto", None) or Decimal("0.00"),
            })
        return rows

    def recalculate_totals(self) -> None:
        items = self.items.all()
        subtotal = sum((item.line_subtotal or Decimal("0.00") for item in items), Decimal("0.00"))
        # Descuento solo sobre productos (cámaras)
        discount_pct = getattr(self, "special_discount_percent", None) or Decimal("0.00")
        self.special_discount_amount = (
            subtotal * discount_pct / Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        products_total = subtotal - self.special_discount_amount
        if products_total < 0:
            products_total = Decimal("0.00")
        # Base para IVA = solo productos (con descuento). Opcionales van aparte.
        base_for_iva = products_total
        tax_rate = self.tax_rate or Decimal("0.00")
        try:
            tax_amount = (
                base_for_iva * tax_rate / Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            tax_amount = Decimal("0.00")
        optional_total = self.get_optional_services_total()
        total = base_for_iva + tax_amount + optional_total
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.total = total
        if self.pk is not None:
            Quote.objects.filter(pk=self.pk).update(
                subtotal=self.subtotal,
                special_discount_amount=self.special_discount_amount,
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
    discount_percent = models.DecimalField(
        "Descuento (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_amount = models.DecimalField(
        "Descuento (monto)", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    line_subtotal = models.DecimalField(
        "Subtotal línea", max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    configuration_notes = models.TextField("Notas de configuración", blank=True)
    group_name = models.CharField(
        "Grupo",
        max_length=120,
        blank=True,
        help_text="Nombre del grupo (ej: Sistema de Conteo de Personas). Items con el mismo grupo se agrupan en la tabla.",
    )
    order_in_group = models.PositiveSmallIntegerField(
        "Orden en grupo",
        default=0,
        help_text="Orden dentro del grupo (0=primero).",
    )

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
        discount_pct = self.discount_percent if hasattr(self, "discount_percent") else None
        if discount_pct is not None and (discount_pct < 0 or discount_pct > 100):
            raise ValidationError(
                {"discount_percent": "El descuento debe ser un porcentaje entre 0 y 100."}
            )
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
    def save(self, *args, **kwargs):
        if self.quantity is None:
            self.line_subtotal = Decimal("0.00")
            return super().save(*args, **kwargs)
        # Precio fijo: siempre tomar del catálogo
        if self.camera_model_id:
            self.unit_price = self.camera_model.base_price
        unit_price = self.unit_price or Decimal("0.00")
        quantity = self.quantity or 0
        discount_pct = getattr(self, "discount_percent", None) or Decimal("0.00")
        line_before_discount = unit_price * quantity
        self.discount_amount = (line_before_discount * discount_pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        line_subtotal = line_before_discount - self.discount_amount
        if line_subtotal < 0:
            line_subtotal = Decimal("0.00")
        self.line_subtotal = line_subtotal
        super().save(*args, **kwargs)
