from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = "Crea grupos y asigna permisos base para el sistema."

    def handle(self, *args, **options):
        model_codenames = [
            "customer",
            "customercontact",
            "cameramodel",
            "quote",
            "quoteitem",
        ]
        perms = Permission.objects.filter(
            Q(codename__startswith="add_")
            | Q(codename__startswith="change_")
            | Q(codename__startswith="delete_")
            | Q(codename__startswith="view_"),
            content_type__model__in=model_codenames,
        )

        admin_group, _ = Group.objects.get_or_create(name="Admin")
        ventas_group, _ = Group.objects.get_or_create(name="Ventas")
        lectura_group, _ = Group.objects.get_or_create(name="Solo_lectura")

        admin_group.permissions.set(perms)

        ventas_group.permissions.set(
            perms.exclude(codename__startswith="delete_")
        )

        lectura_group.permissions.set(
            perms.filter(codename__startswith="view_")
        )

        self.stdout.write(self.style.SUCCESS("Grupos y permisos configurados."))
