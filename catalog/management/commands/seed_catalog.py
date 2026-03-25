from decimal import Decimal
from django.core.management.base import BaseCommand
from catalog.models import CameraModel

class Command(BaseCommand):
    help = 'Carga el catálogo con modelos de cámaras de conteo. Los precios base son USD de lista (ilustrativos; ajusta a tu costo real).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Elimina todos los modelos del catálogo antes de cargar (¡cuidado en producción!).')

    def handle(self, *args, **options):
        if options.get('reset'):
            deleted, _ = CameraModel.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} modelos del catálogo.'))
        cameras = [('XOV-PC2SE', 'Xovis', 'Sensor de conteo PC2SE', 'Sensor de conteo de personas. Alturas de montaje 2–6 m. PoE, extensiones IA (género, dirección, mascarilla).', Decimal('1425.00')), ('XOV-PC2SE-L', 'Xovis', 'Sensor PC2SE-L (rango extendido)', 'Versión de rango extendido del PC2SE. Ideal para puertas anchas o pasillos.', Decimal('1560.00')), ('XOV-PC2SE-UL', 'Xovis', 'Sensor PC2SE-UL (ultra largo alcance)', 'Alcance ultra largo. Para zonas de gran aforo o alturas superiores.', Decimal('1690.00')), ('XOV-PC2RE', 'Xovis', 'Sensor PC2RE (WiFi/Bluetooth)', 'Conteo de personas con WiFi y módulo de monitoreo Bluetooth. Misma precisión que la serie PC2SE.', Decimal('1490.00')), ('XOV-PC2RE-O', 'Xovis', 'Sensor PC2RE-O (exterior)', 'Versión para exterior, resistente a intemperie. WiFi/Bluetooth.', Decimal('1625.00')), ('XOV-PC3SE', 'Xovis', 'Sensor PC3SE (alturas altas)', 'Para montaje en alturas elevadas y zonas de gran superficie. Mayor cobertura.', Decimal('1790.00')), ('XOV-PC3SE-L', 'Xovis', 'Sensor PC3SE-L (rango extendido)', 'PC3 con rango extendido. Retail, atrios, estaciones.', Decimal('1925.00')), ('XOV-IBEX2', 'Xovis', 'IBEX 2 – Contador 3D', 'Sensor 3D de conteo en tiempo real. Entradas/salidas, direcciones, estadías.', Decimal('2100.00')), ('XOV-IBEX3', 'Xovis', 'IBEX 3 – Contador 3D avanzado', 'Versión avanzada IBEX. Filtros por altura, exclusión de carritos, análisis de colas.', Decimal('2325.00')), ('BKS-3D-G2', 'Brickstream', 'Brickstream 3D Gen 2', 'Sensor 3D estereoscópico. Conteo entradas/salidas, colas, tiempo de espera, presencia. Filtro por altura y empleados.', Decimal('1975.00')), ('BKS-3D-G2-6M', 'Brickstream', 'Brickstream 3D Gen 2 (lente 6 mm)', '3D Gen 2 con lente 6 mm para montaje 6–14 m. Ideal atrios y grandes superficies.', Decimal('2075.00')), ('BKS-2400', 'Brickstream', 'Brickstream 2400', 'Sensor de conteo 3D para retail. Entradas/salidas y métricas de tráfico.', Decimal('1340.00')), ('BKS-2600', 'Brickstream', 'Brickstream 2600', 'Sensor de analytics 3D. Conteo de personas, direcciones, detección de colas.', Decimal('1560.00')), ('SMT-3D-RETAIL', 'Sensormatic', 'Sensormatic 3D Retail Analytics', 'Solución 3D para retail. Conteo preciso, filtro niños/empleados, integración con software de analytics.', Decimal('2140.00')), ('CNT-AX100', 'Axis', 'Contador de personas AX100', 'Cámara de conteo de personas para entradas/salidas. Interior, PoE.', Decimal('925.00')), ('CNT-AX200', 'Axis', 'Contador de personas AX200', 'Contador de personas con analytics mejorado. Ideal accesos y retail.', Decimal('1240.00')), ('CNT-HK310', 'Hikvision', 'Conteo de personas People Counting HK310', 'Cámara de conteo de personas Hikvision. Entrada/salida y aforo.', Decimal('810.00')), ('CNT-HK420', 'Hikvision', 'Conteo de personas People Counting HK420', 'Modelo avanzado de conteo. Múltiples líneas de conteo y reportes.', Decimal('1075.00')), ('CNT-DA500', 'Dahua', 'Conteo inteligente DA500', 'Cámara de conteo inteligente Dahua. Análisis de tráfico y aforo.', Decimal('990.00'))]
        created = 0
        updated = 0
        for code, brand, name, description, price in cameras:
            obj, was_created = CameraModel.objects.update_or_create(model_code=code, defaults={'brand': brand, 'name': name, 'description': description, 'base_price': price, 'is_active': True})
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Catálogo listo. {created} modelos nuevos, {updated} actualizados (precio/datos), total definidos: {len(cameras)}.'))
