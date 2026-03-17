#!/usr/bin/env python
"""
Exporta datos locales (SQLite) a un archivo JSON para importar en producción.
Ejecutar en tu máquina local, desde la raíz del proyecto:

    python scripts/export_data.py

Esto crea data_export.json con usuarios, clientes, contactos, cotizaciones, catálogo, etc.
"""
import subprocess
import sys

# Apps y modelos a exportar
# Incluimos auth.User porque las cotizaciones tienen FK a vendedor
OUTPUT = "data_export.json"
EXCLUDE = ["sessions.session", "admin.logentry"]  # sesiones y logs no necesarios

def main():
    excludes = " ".join(f"--exclude {e}" for e in EXCLUDE)
    cmd = f"python manage.py dumpdata auth.User catalog customers quotes accounts {excludes} --indent 2 -o {OUTPUT}"
    print(f"Exportando datos a {OUTPUT}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"Listo. Archivo: {OUTPUT}")
    print("\nPara importar en Railway:")
    print("  1. Sube data_export.json a tu proyecto (o pégalo en una variable)")
    print("  2. Ejecuta: railway run python manage.py loaddata data_export.json")

if __name__ == "__main__":
    main()
