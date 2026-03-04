#!/bin/bash
# Actualizar aplicación Cotizaciones en Contabo (ejecutar desde el directorio del proyecto)
set -e

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$APP_DIR"

echo ">>> Actualizando desde git..."
git pull

echo ">>> Instalando dependencias..."
./venv/bin/pip install -r requirements.txt

echo ">>> Recogiendo archivos estáticos..."
./venv/bin/python manage.py collectstatic --noinput

echo ">>> Reiniciando servicio..."
sudo systemctl restart cotizaciones

echo ">>> Listo. Migraciones se ejecutan al iniciar (scripts/start.py)."
