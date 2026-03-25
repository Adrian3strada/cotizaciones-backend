from django.core.management.base import BaseCommand
from django.utils import timezone
from quotes.models import Quote

class Command(BaseCommand):
    help = 'Marca como expiradas las cotizaciones vencidas.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        expired_count = Quote.objects.filter(status__in=[Quote.STATUS_DRAFT, Quote.STATUS_SENT], valid_until__lt=today).update(status=Quote.STATUS_EXPIRED)
        self.stdout.write(self.style.SUCCESS(f'Cotizaciones expiradas actualizadas: {expired_count}'))
