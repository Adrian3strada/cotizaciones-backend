from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Carga datos de demostración completos: catálogo, clientes y cotizaciones desde el 1 de enero del año en curso hasta hoy (cotizaciones con notes=SEED_QUOTES).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Regenera cotizaciones SEED_QUOTES (--reset en seed_quotes). El catálogo y clientes usan get_or_create (no borra).')

    def handle(self, *args, **options):
        self.stdout.write('Catálogo (seed_catalog)...')
        call_command('seed_catalog')
        self.stdout.write('Clientes (seed_customers)...')
        call_command('seed_customers')
        self.stdout.write('Cotizaciones enero -> hoy (seed_quotes)...')
        if options.get('reset'):
            call_command('seed_quotes', reset=True)
        else:
            call_command('seed_quotes')
        self.stdout.write(self.style.SUCCESS('Listo. Opcional: python manage.py setup_groups'))
