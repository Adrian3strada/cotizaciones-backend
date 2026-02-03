from django.db import models
from django.urls import reverse


class CameraModel(models.Model):
    CURRENCY_MXN = "MXN"
    CURRENCY_USD = "USD"
    CURRENCY_CHOICES = [
        (CURRENCY_MXN, "MXN"),
        (CURRENCY_USD, "USD"),
    ]

    brand = models.CharField("Marca", max_length=100, blank=True)
    model_code = models.CharField("Código de modelo", max_length=100, unique=True)
    name = models.CharField("Nombre", max_length=255, blank=True)
    description = models.TextField("Descripción", blank=True)
    datasheet_file = models.FileField(
        "Ficha técnica", upload_to="datasheets/", blank=True, null=True
    )
    base_price = models.DecimalField("Precio base", max_digits=14, decimal_places=2)
    currency = models.CharField("Moneda", max_length=3, choices=CURRENCY_CHOICES)
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Modelo de cámara"
        verbose_name_plural = "Modelos de cámara"
        ordering = ["model_code"]

    def __str__(self) -> str:
        display = self.name or self.model_code
        return f"{display}"

    def get_absolute_url(self):
        return reverse("catalog:detail", kwargs={"pk": self.pk})
