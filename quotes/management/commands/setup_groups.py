from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = "Crea grupos y asigna permisos base para el sistema."

    def handle(self, *args, **options):
        # Permisos de negocio: clientes, catálogo, cotizaciones
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

        # Permisos de administración de usuarios (solo grupo Admin)
        auth_perms = Permission.objects.filter(
            content_type__app_label="auth",
            content_type__model="user",
            codename__in=("view_user", "add_user", "change_user", "delete_user"),
        )

        admin_group, _ = Group.objects.get_or_create(name="Admin")
        ventas_group, _ = Group.objects.get_or_create(name="Ventas")
        lectura_group, _ = Group.objects.get_or_create(name="Solo_lectura")

        # Admin: todos los permisos de negocio + gestión de usuarios
        admin_group.permissions.set(list(perms) + list(auth_perms))

        # Ventas: add, change, view (sin delete)
        ventas_group.permissions.set(
            perms.exclude(codename__startswith="delete_")
        )

        # Solo_lectura: solo view
        lectura_group.permissions.set(
            perms.filter(codename__startswith="view_")
        )

        self.stdout.write(self.style.SUCCESS("Grupos y permisos configurados."))
