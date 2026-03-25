from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Verifica grupos y permisos de un usuario. Uso: verify_user_perms <username>'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='?', help='Nombre de usuario (opcional)')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options.get('username')
        if username:
            users = User.objects.filter(username=username)
        else:
            users = User.objects.all().order_by('username')
        if not users.exists():
            self.stdout.write(self.style.WARNING(f"No se encontró usuario: {username or 'ninguno'}"))
            return
        for user in users:
            groups = list(user.groups.values_list('name', flat=True))
            has_view_customer = user.has_perm('customers.view_customer')
            self.stdout.write(f'\n{user.username}:')
            self.stdout.write(f"  Grupos: {groups or '(ninguno)'}")
            self.stdout.write(f'  customers.view_customer: {has_view_customer}')
            if not has_view_customer and (not user.is_superuser):
                self.stdout.write(self.style.WARNING("  -> Asigna el grupo 'Solo_lectura' y vuelve a iniciar sesion."))
