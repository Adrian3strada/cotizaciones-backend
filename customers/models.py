from django.db import models
from django.urls import reverse

class Customer(models.Model):
    name = models.CharField('Nombre', max_length=255)
    country_code = models.CharField('País (ISO)', max_length=2, default='MX', blank=True, help_text='MX = cliente en México (cotización usual en pesos). Otro código (ej. US) sugiere cotización en USD.')
    rfc = models.CharField('RFC', max_length=50, blank=True)
    website = models.URLField('Sitio web', blank=True)
    street_address = models.CharField('Calle y No.', max_length=255, blank=True)
    neighborhood = models.CharField('Colonia', max_length=150, blank=True)
    city = models.CharField('Ciudad', max_length=150, blank=True)
    postal_code = models.CharField('C.P.', max_length=10, blank=True)
    phone = models.CharField('Teléfono', max_length=50, blank=True)
    mobile = models.CharField('Celular', max_length=50, blank=True)
    billing_address = models.TextField('Dirección de facturación', blank=True)
    shipping_address = models.TextField('Dirección de envío', blank=True)
    notes = models.TextField('Notas', blank=True)
    is_active = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def default_quote_currency(self) -> str:
        code = (self.country_code or 'MX').strip().upper() or 'MX'
        return 'MXN' if code == 'MX' else 'USD'

    def get_absolute_url(self):
        return reverse('customers:detail', kwargs={'pk': self.pk})

class CustomerContact(models.Model):
    customer = models.ForeignKey(Customer, verbose_name='Cliente', on_delete=models.CASCADE, related_name='contacts')
    full_name = models.CharField('Nombre completo', max_length=255)
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Teléfono', max_length=50, blank=True)
    mobile = models.CharField('Celular', max_length=50, blank=True)
    position = models.CharField('Puesto', max_length=100, blank=True)
    is_primary = models.BooleanField('Es principal', default=False)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'
        ordering = ['full_name']

    def __str__(self) -> str:
        return f'{self.full_name} ({self.customer.name})'
