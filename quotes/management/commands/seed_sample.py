from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import CameraModel
from customers.models import Customer, CustomerContact
from quotes.models import Quote, QuoteItem


class Command(BaseCommand):
    help = "Crea datos de ejemplo para pruebas rápidas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina datos de ejemplo existentes antes de recrearlos.",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        user = user_model.objects.filter(is_staff=True).first()
        if not user:
            user = user_model.objects.create_user(
                username="ventas",
                password="ventas123",
                is_staff=True,
                email="ventas@ejemplo.com",
            )

        if options.get("reset"):
            QuoteItem.objects.filter(quote__notes="SEED_SAMPLE").delete()
            Quote.objects.filter(notes="SEED_SAMPLE").delete()
            CustomerContact.objects.filter(customer__notes="SEED_SAMPLE").delete()
            Customer.objects.filter(notes="SEED_SAMPLE").delete()
            self.stdout.write(self.style.SUCCESS("Datos de ejemplo eliminados."))

        if Quote.objects.filter(notes="SEED_SAMPLE").exists():
            self.stdout.write(self.style.WARNING("Datos de ejemplo ya existen."))
            return

        customers = [
            {
                "name": "Supermercados La Esperanza SA de CV",
                "rfc": "SLE9805123A1",
                "billing_address": "Av. Reforma 123, Col. Centro, CDMX",
                "shipping_address": "Cedis Norte, Parque Industrial 45, Tlalnepantla, Edo. Mex.",
                "contact": {
                    "full_name": "Mariana Torres",
                    "email": "mariana.torres@laesperanza.com.mx",
                    "phone": "55-3567-8899",
                    "position": "Compras",
                },
            },
            {
                "name": "Plaza Comercial Gran Rio",
                "rfc": "PCR0402149B7",
                "billing_address": "Blvd. Riveras 987, Monterrey, NL",
                "shipping_address": "Acceso Proveedores, Blvd. Riveras 987, Monterrey, NL",
                "contact": {
                    "full_name": "Luis Alberto García",
                    "email": "lgarcia@granrio.mx",
                    "phone": "81-2244-5566",
                    "position": "Gerente de Operaciones",
                },
            },
            {
                "name": "Centro Corporativo Azul",
                "rfc": "CCA1109268K2",
                "billing_address": "Av. Universidad 450, Guadalajara, Jal.",
                "shipping_address": "Recepción Torre B, Av. Universidad 450, Guadalajara, Jal.",
                "contact": {
                    "full_name": "Paola Hernández",
                    "email": "paola.hernandez@corpazul.mx",
                    "phone": "33-1987-3322",
                    "position": "Facilities",
                },
            },
            {
                "name": "Aeropuerto Regional del Bajio",
                "rfc": "ARB0208155Q4",
                "billing_address": "Carretera Silao-León Km 7.5, Silao, Gto.",
                "shipping_address": "Terminal 1, Oficina de Seguridad, Silao, Gto.",
                "contact": {
                    "full_name": "Jorge Ramírez",
                    "email": "jorge.ramirez@arb.mx",
                    "phone": "477-215-7788",
                    "position": "Seguridad",
                },
            },
        ]
        customer_objs = []
        for data in customers:
            customer, _ = Customer.objects.get_or_create(
                name=data["name"],
                defaults={
                    "rfc": data["rfc"],
                    "website": "https://www.brandarrays.com/",
                    "street_address": data["billing_address"],
                    "neighborhood": "Col. Centro",
                    "city": "CDMX",
                    "postal_code": "06000",
                    "phone": "55 8664 9500 ext. 227",
                    "mobile": "55 8581 1502",
                    "billing_address": data["billing_address"],
                    "shipping_address": data["shipping_address"],
                    "notes": "SEED_SAMPLE",
                },
            )
            customer_objs.append(customer)
            CustomerContact.objects.get_or_create(
                customer=customer,
                full_name=data["contact"]["full_name"],
                defaults={
                    "email": data["contact"]["email"],
                    "phone": data["contact"]["phone"],
                    "position": data["contact"]["position"],
                    "is_primary": True,
                },
            )

        camera_models = [
            ("CNT-AX100", "Axis", "Contador AX100", Decimal("925.00")),
            ("CNT-AX200", "Axis", "Contador AX200", Decimal("1240.00")),
            ("CNT-HK310", "Hikvision", "Conteo People HK310", Decimal("810.00")),
            ("CNT-HK420", "Hikvision", "Conteo People HK420", Decimal("1075.00")),
            ("CNT-DA500", "Dahua", "Conteo Inteligente DA500", Decimal("990.00")),
        ]
        camera_objs = []
        for code, brand, name, price in camera_models:
            camera, _ = CameraModel.objects.get_or_create(
                model_code=code,
                defaults={
                    "brand": brand,
                    "name": name,
                    "base_price": price,
                },
            )
            camera_objs.append(camera)

        today = timezone.localdate()
        quotes_data = [
            (customer_objs[0], camera_objs[0], 6, camera_objs[2], 2, Quote.STATUS_DRAFT),
            (customer_objs[1], camera_objs[1], 4, camera_objs[3], 2, Quote.STATUS_SENT),
            (customer_objs[2], camera_objs[2], 3, camera_objs[4], 1, Quote.STATUS_ACCEPTED),
            (customer_objs[3], camera_objs[3], 5, camera_objs[0], 2, Quote.STATUS_REJECTED),
            (customer_objs[0], camera_objs[4], 2, camera_objs[1], 1, Quote.STATUS_DRAFT),
        ]

        for customer, camera_a, qty_a, camera_b, qty_b, status in quotes_data:
            contact = customer.contacts.first()
            quote = Quote.objects.create(
                customer=customer,
                contact=contact,
                sales_user=user,
                valid_until=today + timezone.timedelta(days=30),
                currency=Quote.CURRENCY_MXN,
                usd_mxn_rate=Decimal("20.00"),
                notes="SEED_SAMPLE",
                terms="Entrega 10-15 días hábiles. Pago 50% anticipo, 50% contra entrega.",
            )
            QuoteItem.objects.create(
                quote=quote,
                camera_model=camera_a,
                quantity=qty_a,
                unit_price=camera_a.base_price,
            )
            QuoteItem.objects.create(
                quote=quote,
                camera_model=camera_b,
                quantity=qty_b,
                unit_price=camera_b.base_price,
            )
            quote.status = status
            quote.save()

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo creados (varios)."))
