#!/usr/bin/env python
"""Script de inicio: migraciones + superusuario opcional + gunicorn."""
import os
import subprocess
import sys


def run(cmd, check=True):
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result.returncode


def main():
    run("python manage.py migrate --noinput")

    # Crear superusuario si las variables están definidas
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL") or "admin@sisconper.com"

    if username and password:
        # Django requiere email válido; usar default si no está definido
        if not os.environ.get("DJANGO_SUPERUSER_EMAIL"):
            os.environ["DJANGO_SUPERUSER_EMAIL"] = email
        run("python manage.py createsuperuser --noinput", check=False)

    os.execvp("gunicorn", [
        "gunicorn", "cotizaciones_project.wsgi:application"
    ])


if __name__ == "__main__":
    main()
