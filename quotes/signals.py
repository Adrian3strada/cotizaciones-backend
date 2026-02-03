from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from quotes.models import QuoteItem


@receiver(post_save, sender=QuoteItem)
def quote_item_saved(sender, instance, **kwargs):
    instance.quote.recalculate_totals()


@receiver(post_delete, sender=QuoteItem)
def quote_item_deleted(sender, instance, **kwargs):
    instance.quote.recalculate_totals()
