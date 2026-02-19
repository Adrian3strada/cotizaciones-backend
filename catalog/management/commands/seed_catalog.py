from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import CameraModel


class Command(BaseCommand):
    help = "Carga el catálogo con modelos de cámaras de conteo de personas (Xovis, Brickstream, Axis, Hikvision, Dahua)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina todos los modelos del catálogo antes de cargar (¡cuidado en producción!).",
        )

    def handle(self, *args, **options):
        if options.get("reset"):
            deleted, _ = CameraModel.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Eliminados {deleted} modelos del catálogo."))

        # (model_code, brand, name, description, base_price, currency)
        cameras = [
            # --- Xovis ---
            (
                "XOV-PC2SE",
                "Xovis",
                "Sensor de conteo PC2SE",
                "Sensor de conteo de personas. Alturas de montaje 2–6 m. PoE, extensiones IA (género, dirección, mascarilla).",
                Decimal("28500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC2SE-L",
                "Xovis",
                "Sensor PC2SE-L (rango extendido)",
                "Versión de rango extendido del PC2SE. Ideal para puertas anchas o pasillos.",
                Decimal("31200.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC2SE-UL",
                "Xovis",
                "Sensor PC2SE-UL (ultra largo alcance)",
                "Alcance ultra largo. Para zonas de gran aforo o alturas superiores.",
                Decimal("33800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC2RE",
                "Xovis",
                "Sensor PC2RE (WiFi/Bluetooth)",
                "Conteo de personas con WiFi y módulo de monitoreo Bluetooth. Misma precisión que la serie PC2SE.",
                Decimal("29800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC2RE-O",
                "Xovis",
                "Sensor PC2RE-O (exterior)",
                "Versión para exterior, resistente a intemperie. WiFi/Bluetooth.",
                Decimal("32500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC3SE",
                "Xovis",
                "Sensor PC3SE (alturas altas)",
                "Para montaje en alturas elevadas y zonas de gran superficie. Mayor cobertura.",
                Decimal("35800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-PC3SE-L",
                "Xovis",
                "Sensor PC3SE-L (rango extendido)",
                "PC3 con rango extendido. Retail, atrios, estaciones.",
                Decimal("38500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-IBEX2",
                "Xovis",
                "IBEX 2 – Contador 3D",
                "Sensor 3D de conteo en tiempo real. Entradas/salidas, direcciones, estadías.",
                Decimal("42000.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "XOV-IBEX3",
                "Xovis",
                "IBEX 3 – Contador 3D avanzado",
                "Versión avanzada IBEX. Filtros por altura, exclusión de carritos, análisis de colas.",
                Decimal("46500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            # --- Brickstream / Sensormatic ---
            (
                "BKS-3D-G2",
                "Brickstream",
                "Brickstream 3D Gen 2",
                "Sensor 3D estereoscópico. Conteo entradas/salidas, colas, tiempo de espera, presencia. Filtro por altura y empleados.",
                Decimal("39500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "BKS-3D-G2-6M",
                "Brickstream",
                "Brickstream 3D Gen 2 (lente 6 mm)",
                "3D Gen 2 con lente 6 mm para montaje 6–14 m. Ideal atrios y grandes superficies.",
                Decimal("41500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "BKS-2400",
                "Brickstream",
                "Brickstream 2400",
                "Sensor de conteo 3D para retail. Entradas/salidas y métricas de tráfico.",
                Decimal("26800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "BKS-2600",
                "Brickstream",
                "Brickstream 2600",
                "Sensor de analytics 3D. Conteo de personas, direcciones, detección de colas.",
                Decimal("31200.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "SMT-3D-RETAIL",
                "Sensormatic",
                "Sensormatic 3D Retail Analytics",
                "Solución 3D para retail. Conteo preciso, filtro niños/empleados, integración con software de analytics.",
                Decimal("42800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            # --- Axis ---
            (
                "CNT-AX100",
                "Axis",
                "Contador de personas AX100",
                "Cámara de conteo de personas para entradas/salidas. Interior, PoE.",
                Decimal("18500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "CNT-AX200",
                "Axis",
                "Contador de personas AX200",
                "Contador de personas con analytics mejorado. Ideal accesos y retail.",
                Decimal("24800.00"),
                CameraModel.CURRENCY_MXN,
            ),
            # --- Hikvision ---
            (
                "CNT-HK310",
                "Hikvision",
                "Conteo de personas People Counting HK310",
                "Cámara de conteo de personas Hikvision. Entrada/salida y aforo.",
                Decimal("16200.00"),
                CameraModel.CURRENCY_MXN,
            ),
            (
                "CNT-HK420",
                "Hikvision",
                "Conteo de personas People Counting HK420",
                "Modelo avanzado de conteo. Múltiples líneas de conteo y reportes.",
                Decimal("21500.00"),
                CameraModel.CURRENCY_MXN,
            ),
            # --- Dahua ---
            (
                "CNT-DA500",
                "Dahua",
                "Conteo inteligente DA500",
                "Cámara de conteo inteligente Dahua. Análisis de tráfico y aforo.",
                Decimal("19800.00"),
                CameraModel.CURRENCY_MXN,
            ),
        ]

        created = 0
        for code, brand, name, description, price, currency in cameras:
            _, was_created = CameraModel.objects.get_or_create(
                model_code=code,
                defaults={
                    "brand": brand,
                    "name": name,
                    "description": description,
                    "base_price": price,
                    "currency": currency,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo listo. {created} modelos nuevos creados, {len(cameras) - created} ya existían."
            )
        )
