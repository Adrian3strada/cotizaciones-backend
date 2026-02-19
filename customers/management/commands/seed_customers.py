from django.core.management.base import BaseCommand

from customers.models import Customer, CustomerContact


class Command(BaseCommand):
    help = "Carga el catálogo de clientes con varios contactos (usuarios) por cliente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los clientes creados por este comando antes de cargar (por notas SEED_CUSTOMERS).",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            CustomerContact.objects.filter(customer__notes="SEED_CUSTOMERS").delete()
            deleted, _ = Customer.objects.filter(notes="SEED_CUSTOMERS").delete()
            self.stdout.write(self.style.WARNING(f"Eliminados {deleted} clientes de ejemplo."))

        # Cada entrada: (datos del cliente, lista de contactos)
        # Contacto: (full_name, email, phone, position, is_primary)
        clients_data = [
            {
                "name": "Plaza Comercial Galerías Querétaro",
                "rfc": "PCG1204158K9",
                "website": "https://www.galerias.com.mx",
                "street_address": "Av. Constituyentes 100",
                "neighborhood": "Col. Centro",
                "city": "Querétaro",
                "postal_code": "76000",
                "phone": "442 123 4500",
                "billing_address": "Av. Constituyentes 100, Col. Centro, 76000 Querétaro, Qro.",
                "shipping_address": "Oficinas Administración, Nivel 2, Plaza Galerías",
                "contacts": [
                    ("Roberto Mendoza", "roberto.mendoza@galerias.com.mx", "442 123 4501", "Gerente de Operaciones", True),
                    ("Laura Sánchez", "laura.sanchez@galerias.com.mx", "442 123 4502", "Compras y Contratos", False),
                    ("Fernando López", "fernando.lopez@galerias.com.mx", "442 123 4503", "TI y Sistemas", False),
                ],
            },
            {
                "name": "Aeropuerto Internacional de Monterrey",
                "rfc": "AIM850301H27",
                "website": "https://www.oma.aero/mty",
                "street_address": "Carretera Miguel Alemán Km 24",
                "neighborhood": "Apodaca",
                "city": "Monterrey",
                "postal_code": "66600",
                "phone": "81 8288 7000",
                "billing_address": "Carretera Miguel Alemán Km 24, 66600 Apodaca, NL",
                "shipping_address": "Edificio de Operaciones, Área de Seguridad",
                "contacts": [
                    ("Patricia Garza", "p.garza@oma.aero", "81 8288 7010", "Directora de Operaciones", True),
                    ("Ricardo Herrera", "r.herrera@oma.aero", "81 8288 7011", "Jefe de Seguridad", False),
                    ("Ana María Ruiz", "a.ruiz@oma.aero", "81 8288 7012", "Coordinadora de Proyectos", False),
                ],
            },
            {
                "name": "Chedraui S.A. de C.V.",
                "rfc": "CHE850101A12",
                "website": "https://www.chedraui.com.mx",
                "street_address": "Av. Insurgentes Sur 1458",
                "neighborhood": "Col. Actipan",
                "city": "Ciudad de México",
                "postal_code": "03230",
                "phone": "55 5628 9000",
                "billing_address": "Av. Insurgentes Sur 1458, Col. Actipan, 03230 CDMX",
                "shipping_address": "Atención a Proveedores, Cedis correspondiente por zona",
                "contacts": [
                    ("Miguel Ángel Torres", "m.torres@chedraui.com.mx", "55 5628 9010", "Gerente Nacional de Abasto", True),
                    ("Claudia Vega", "c.vega@chedraui.com.mx", "55 5628 9011", "Compras Equipamiento", False),
                    ("Jorge Ramírez", "j.ramirez@chedraui.com.mx", "55 5628 9012", "Proyectos TI", False),
                ],
            },
            {
                "name": "Universidad Autónoma de Guadalajara",
                "rfc": "UAG310101B34",
                "website": "https://www.uag.mx",
                "street_address": "Av. Patria 1201",
                "neighborhood": "Col. Lomas del Valle",
                "city": "Guadalajara",
                "postal_code": "44100",
                "phone": "33 3640 5000",
                "billing_address": "Av. Patria 1201, Col. Lomas del Valle, 44100 Guadalajara, Jal.",
                "shipping_address": "Dirección de Infraestructura, Edificio A",
                "contacts": [
                    ("Dra. Carmen Orozco", "c.orozco@uag.mx", "33 3640 5010", "Directora de Infraestructura", True),
                    ("Ing. Pablo Morales", "p.morales@uag.mx", "33 3640 5011", "Jefe de Mantenimiento", False),
                    ("Lic. Diana Flores", "d.flores@uag.mx", "33 3640 5012", "Compras y Contratos", False),
                ],
            },
            {
                "name": "Hospital Ángeles Puebla",
                "rfc": "HAP920615M56",
                "website": "https://www.hospitalangeles.com",
                "street_address": "Blvd. del Niño Poblano 2510",
                "neighborhood": "Col. Reserva Territorial",
                "city": "Puebla",
                "postal_code": "72260",
                "phone": "222 303 5500",
                "billing_address": "Blvd. del Niño Poblano 2510, 72260 Puebla, Pue.",
                "shipping_address": "Área de Compras, Edificio Administrativo",
                "contacts": [
                    ("Dr. Eduardo Castillo", "e.castillo@hospitalangeles.com", "222 303 5510", "Director Médico", True),
                    ("Ing. Silvia Navarro", "s.navarro@hospitalangeles.com", "222 303 5511", "Facilities y Seguridad", False),
                    ("C.P. Omar Reyes", "o.reyes@hospitalangeles.com", "222 303 5512", "Contraloría y Compras", False),
                ],
            },
            {
                "name": "Grupo Bimbo S.A.B. de C.V.",
                "rfc": "GBM900101A45",
                "website": "https://www.grupobimbo.com",
                "street_address": "Av. Insurgentes Sur 975",
                "neighborhood": "Col. Del Valle",
                "city": "Ciudad de México",
                "postal_code": "03100",
                "phone": "55 5328 7000",
                "billing_address": "Av. Insurgentes Sur 975, Col. Del Valle, 03100 CDMX",
                "shipping_address": "Coordinación por planta o centro de distribución",
                "contacts": [
                    ("Luis Fernando Gómez", "lf.gomez@grupobimbo.com", "55 5328 7010", "Gerente de Proyectos Corporativos", True),
                    ("María José Hernández", "mj.hernandez@grupobimbo.com", "55 5328 7011", "Compras Equipos", False),
                    ("Ing. Andrés Castro", "a.castro@grupobimbo.com", "55 5328 7012", "Automatización y Control", False),
                ],
            },
            {
                "name": "Centro de Convenciones Cintermex",
                "rfc": "CCM040301P78",
                "website": "https://www.cintermex.com",
                "street_address": "Av. Fundadores 100",
                "neighborhood": "Col. Valle Oriente",
                "city": "San Pedro Garza García",
                "postal_code": "66220",
                "phone": "81 8369 5000",
                "billing_address": "Av. Fundadores 100, 66220 San Pedro Garza García, NL",
                "shipping_address": "Oficina de Operaciones, Área de Seguridad",
                "contacts": [
                    ("Ing. Teresa Ríos", "t.rios@cintermex.com", "81 8369 5010", "Directora de Operaciones", True),
                    ("Roberto Núñez", "r.nunez@cintermex.com", "81 8369 5011", "Coordinador de Eventos", False),
                ],
            },
            {
                "name": "Soriana S.A. de C.V.",
                "rfc": "SOR750101K90",
                "website": "https://www.soriana.com",
                "street_address": "Blvd. Revolución 3000",
                "neighborhood": "Col. Primavera",
                "city": "Monterrey",
                "postal_code": "64830",
                "phone": "81 8380 1000",
                "billing_address": "Blvd. Revolución 3000, 64830 Monterrey, NL",
                "shipping_address": "Compras Corporativas, Cedis Soriana",
                "contacts": [
                    ("Gerardo Soto", "g.soto@soriana.com", "81 8380 1010", "Gerente de Abasto Nacional", True),
                    ("Adriana Mejía", "a.mejia@soriana.com", "81 8380 1011", "Compras Equipamiento Tienda", False),
                    ("Carlos Luna", "c.luna@soriana.com", "81 8380 1012", "Proyectos de Retail", False),
                ],
            },
        ]

        created_customers = 0
        created_contacts = 0

        for data in clients_data:
            contacts_list = data.pop("contacts")
            customer, created = Customer.objects.get_or_create(
                name=data["name"],
                defaults={**data, "notes": "SEED_CUSTOMERS"},
            )
            if created:
                created_customers += 1

            for i, (full_name, email, phone, position, is_primary) in enumerate(contacts_list):
                _, contact_created = CustomerContact.objects.get_or_create(
                    customer=customer,
                    full_name=full_name,
                    defaults={
                        "email": email,
                        "phone": phone,
                        "position": position,
                        "is_primary": is_primary,
                    },
                )
                if contact_created:
                    created_contacts += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Clientes: {created_customers} nuevos, {len(clients_data)} en total. "
                f"Contactos: {created_contacts} nuevos."
            )
        )
