"""
Avisa de cotizaciones próximas a vencer (por defecto 3 días).
No las marca como expiradas, solo lista las que vencen pronto.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from quotes.models import Quote


class Command(BaseCommand):
    help = "Lista cotizaciones que vencen en los próximos N días (default: 3)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=3,
            help="Días antes del vencimiento para avisar (default: 3)",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        from datetime import timedelta
        limit_date = today + timedelta(days=options["dias"])
        expiring = Quote.objects.filter(
            status__in=[Quote.STATUS_DRAFT, Quote.STATUS_SENT],
            valid_until__gte=today,
            valid_until__lte=limit_date,
        ).select_related("customer", "sales_user").order_by("valid_until")
        count = expiring.count()
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f"Ninguna cotización vence en los próximos {options['dias']} días.")
            )
            return
        self.stdout.write(
            self.style.WARNING(f"{count} cotización(es) vencen en los próximos {options['dias']} días:\n")
        )
        for q in expiring:
            self.stdout.write(f"  {q.quote_number} | {q.customer.name} | Vence: {q.valid_until} | {q.get_status_display()}")
