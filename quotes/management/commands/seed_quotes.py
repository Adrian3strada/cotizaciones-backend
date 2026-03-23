from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import CameraModel
from customers.models import Customer
from quotes.models import Quote, QuoteItem


# Patrones de ítems: (índice_cámara, cantidad)
_ITEM_PATTERNS = [
    [(0, 3), (1, 2)],
    [(0, 5), (2, 2)],
    [(1, 4), (3, 1)],
    [(2, 6), (4, 2)],
    [(0, 2), (5, 3)],
    [(3, 8), (1, 2)],
    [(4, 3), (6, 4)],
    [(0, 10)],
    [(7, 2), (8, 2)],
    [(2, 5), (9, 1)],
    [(1, 3), (4, 3)],
    [(6, 4), (10, 2)],
]

_STATUS_CYCLE = [
    Quote.STATUS_DRAFT,
    Quote.STATUS_SENT,
    Quote.STATUS_ACCEPTED,
    Quote.STATUS_SENT,
    Quote.STATUS_REJECTED,
    Quote.STATUS_DRAFT,
    Quote.STATUS_ACCEPTED,
    Quote.STATUS_EXPIRED,
    Quote.STATUS_SENT,
]

_DISCOUNTS = [None, Decimal("5.00"), None, Decimal("10.00"), None, Decimal("8.00"), Decimal("3.00"), None]


class Command(BaseCommand):
    help = (
        "Crea cotizaciones de ejemplo (notes=SEED_QUOTES) repartidas desde el 1 de enero "
        "del año en curso hasta hoy. Requiere clientes con contactos y modelos en catálogo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina antes las cotizaciones SEED_QUOTES existentes.",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            QuoteItem.objects.filter(quote__notes="SEED_QUOTES").delete()
            deleted, _ = Quote.objects.filter(notes="SEED_QUOTES").delete()
            self.stdout.write(self.style.WARNING(f"Eliminadas {deleted} cotizaciones SEED_QUOTES anteriores."))
        elif Quote.objects.filter(notes="SEED_QUOTES").exists():
            self.stdout.write(
                self.style.WARNING(
                    "Ya existen cotizaciones SEED_QUOTES. Pasa --reset para regenerarlas desde enero."
                )
            )
            return

        User = get_user_model()
        staff_users = list(User.objects.filter(is_staff=True).order_by("id"))
        if not staff_users:
            user = User.objects.create_user(
                username="ventas", password="ventas123", is_staff=True, email="ventas@ejemplo.com"
            )
            staff_users = [user]
            self.stdout.write(self.style.WARNING("Creado usuario staff 'ventas' para asignar cotizaciones."))

        customers = list(
            Customer.objects.filter(contacts__isnull=False).distinct().order_by("name")[:20]
        )
        cameras = list(CameraModel.objects.filter(is_active=True).order_by("model_code"))

        if not customers:
            self.stdout.write(self.style.ERROR("No hay clientes con contactos. Ejecuta: python manage.py seed_customers"))
            return
        if not cameras:
            self.stdout.write(self.style.ERROR("No hay modelos en el catálogo. Ejecuta: python manage.py seed_catalog"))
            return

        today = timezone.localdate()
        year_start = date(today.year, 1, 1)
        span_days = max(1, (today - year_start).days + 1)
        # ~1 cotización cada 3–4 días del rango, entre 20 y 90 filas
        num = min(90, max(20, span_days // 3))

        terms = "Entrega 10-15 días hábiles. Pago 50% anticipo, 50% contra entrega. Garantía 1 año."
        tc = Decimal("20.00")

        created = 0
        for i in range(num):
            day_offset = int(round(i * (span_days - 1) / max(1, num - 1))) if num > 1 else 0
            issue_date = year_start + timedelta(days=day_offset)
            if issue_date > today:
                issue_date = today

            status = _STATUS_CYCLE[i % len(_STATUS_CYCLE)]
            discount = _DISCOUNTS[i % len(_DISCOUNTS)]
            pattern = _ITEM_PATTERNS[i % len(_ITEM_PATTERNS)]

            customer = customers[i % len(customers)]
            contact = customer.contacts.filter(is_primary=True).first() or customer.contacts.first()
            sales_user = staff_users[i % len(staff_users)]

            # Evitar que save() marque EXPIRED salvo cuando el estatus lo pide explícitamente
            if status == Quote.STATUS_EXPIRED:
                valid_until = issue_date + timedelta(days=14)
            else:
                valid_until = max(issue_date + timedelta(days=30), today + timedelta(days=7))

            quote = Quote(
                customer=customer,
                contact=contact,
                sales_user=sales_user,
                issue_date=issue_date,
                valid_until=valid_until,
                currency=Quote.CURRENCY_MXN,
                usd_mxn_rate=tc,
                tax_rate=Decimal("16.00"),
                special_discount_percent=discount or Decimal("0.00"),
                notes="SEED_QUOTES",
                terms=terms,
            )

            opt = i % 9
            if opt in (1, 4, 7):
                quote.cableado = True
                quote.cableado_monto = Decimal("3500.00")
            if opt in (2, 4, 8):
                quote.instalacion = True
                quote.instalacion_monto = Decimal("8500.00")
            if opt in (3, 5, 7, 8):
                quote.poe = True
                quote.poe_monto = Decimal("2500.00")

            quote.save()

            for cam_idx, qty in pattern:
                cam = cameras[cam_idx % len(cameras)]
                QuoteItem.objects.create(
                    quote=quote,
                    camera_model=cam,
                    quantity=qty,
                    unit_price=cam.base_price,
                )

            quote.recalculate_totals()
            quote.status = status
            quote.save()

            # Alinear timestamps con la fecha de emisión (reportes / listas)
            ts = datetime.combine(issue_date, time(10, 30))
            if settings.USE_TZ:
                ts = timezone.make_aware(ts, timezone.get_current_timezone())
            Quote.objects.filter(pk=quote.pk).update(created_at=ts, updated_at=ts)

            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Creadas {created} cotizaciones SEED_QUOTES "
                f"({year_start.isoformat()} -> {today.isoformat()})."
            )
        )
