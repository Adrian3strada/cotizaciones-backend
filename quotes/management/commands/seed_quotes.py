from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import CameraModel
from customers.models import Customer
from quotes.models import Quote, QuoteItem


class Command(BaseCommand):
    help = "Crea varias cotizaciones de ejemplo (diferentes clientes, estados e ítems)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina las cotizaciones creadas por este comando (notes=SEED_QUOTES) antes de cargar.",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            QuoteItem.objects.filter(quote__notes="SEED_QUOTES").delete()
            deleted, _ = Quote.objects.filter(notes="SEED_QUOTES").delete()
            self.stdout.write(self.style.WARNING(f"Eliminadas {deleted} cotizaciones de ejemplo."))

        User = get_user_model()
        user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.create_user(username="ventas", password="ventas123", is_staff=True)
            self.stdout.write(self.style.WARNING("Creado usuario 'ventas' para asignar cotizaciones."))

        customers = list(
            Customer.objects.filter(contacts__isnull=False).distinct().order_by("name")[:10]
        )
        cameras = list(CameraModel.objects.filter(is_active=True).order_by("model_code")[:15])

        if not customers:
            self.stdout.write(self.style.ERROR("No hay clientes con contactos. Ejecuta: python manage.py seed_customers"))
            return
        if not cameras:
            self.stdout.write(self.style.ERROR("No hay modelos en el catálogo. Ejecuta: python manage.py seed_catalog"))
            return

        today = timezone.localdate()
        terms = "Entrega 10-15 días hábiles. Pago 50% anticipo, 50% contra entrega. Garantía 1 año."

        # (customer_index, list of (camera_index, qty), status, optional: discount_pct, cableado, instalacion, days_offset_issue)
        quotes_spec = [
            (0, [(0, 4), (1, 2)], Quote.STATUS_DRAFT, None, False, False, 0),
            (1, [(2, 6), (3, 2)], Quote.STATUS_SENT, None, False, False, 2),
            (2, [(4, 3), (5, 1)], Quote.STATUS_ACCEPTED, Decimal("5.00"), True, True, 5),
            (3, [(6, 8), (7, 4)], Quote.STATUS_REJECTED, None, False, False, 10),
            (4, [(8, 2), (9, 2), (10, 1)], Quote.STATUS_DRAFT, Decimal("10.00"), False, True, 0),
            (0, [(1, 3), (2, 3)], Quote.STATUS_SENT, None, True, False, 3),
            (5, [(11, 5), (12, 2)], Quote.STATUS_ACCEPTED, Decimal("8.00"), True, True, 7),
            (6, [(0, 10)], Quote.STATUS_DRAFT, None, False, False, 0),
            (7, [(13, 4), (14, 2)], Quote.STATUS_SENT, Decimal("3.00"), False, True, 1),
            (1, [(4, 2), (6, 2), (8, 1)], Quote.STATUS_DRAFT, None, False, False, 0),
            (2, [(3, 6)], Quote.STATUS_EXPIRED, None, False, False, -45),
            (3, [(5, 4), (7, 2)], Quote.STATUS_ACCEPTED, Decimal("12.00"), True, True, 14),
        ]

        created = 0
        for spec in quotes_spec:
            cust_idx = spec[0] % len(customers)
            customer = customers[cust_idx]
            contact = customer.contacts.filter(is_primary=True).first() or customer.contacts.first()

            issue_date = today + timedelta(days=spec[6])
            valid_until = issue_date + timedelta(days=30)

            quote = Quote(
                customer=customer,
                contact=contact,
                sales_user=user,
                issue_date=issue_date,
                valid_until=valid_until,
                currency=Quote.CURRENCY_MXN,
                tax_rate=Decimal("16.00"),
                special_discount_percent=spec[3] or Decimal("0.00"),
                notes="SEED_QUOTES",
                terms=terms,
            )
            if spec[4]:
                quote.cableado = True
                quote.cableado_monto = Decimal("3500.00")
            if spec[5]:
                quote.instalacion = True
                quote.instalacion_monto = Decimal("8500.00")
            quote.save()

            for cam_idx, qty in spec[1]:
                cam = cameras[cam_idx % len(cameras)]
                QuoteItem.objects.create(
                    quote=quote,
                    camera_model=cam,
                    quantity=qty,
                    unit_price=cam.base_price,
                )

            quote.recalculate_totals()
            quote.status = spec[2]
            quote.save()
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Cotizaciones de ejemplo creadas: {created} nuevas.")
        )
