#!/usr/bin/env python
"""Script de inicio: migraciones + superusuario opcional + gunicorn."""
import os
import subprocess
import sys


def run(cmd, check=True, env=None):
    result = subprocess.run(cmd, shell=True, env=env or os.environ)
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result.returncode


def main():
    run("python manage.py migrate --noinput")

    # Crear superusuario si las variables están definidas
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
    email_raw = (os.environ.get("DJANGO_SUPERUSER_EMAIL") or "").strip()
    # Django exige email con formato válido (debe contener @)
    email = email_raw if "@" in email_raw else "admin@sisconper.com"

    if username and password:
        env = os.environ.copy()
        env["DJANGO_SUPERUSER_EMAIL"] = email
        run("python manage.py createsuperuser --noinput", check=False, env=env)

    port = os.environ.get("PORT", "8000")
    os.execvp("gunicorn", [
        "gunicorn", "cotizaciones_project.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
    ])


if __name__ == "__main__":
    main()
