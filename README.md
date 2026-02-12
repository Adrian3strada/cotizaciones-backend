# Cotizaciones Project (Django)

MVP monolítico en Django para reemplazar cotizaciones en Excel.

## Requisitos

- Python 3.11+
- Conda (opcional, pero recomendado)
- SQLite (dev) o PostgreSQL (opcional)

## Configuración rápida

```bash
conda create -n cotizaciones python=3.11 -y
conda activate cotizaciones
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_groups
python manage.py runserver
```

## Base de datos PostgreSQL (opcional)

Define estas variables de entorno para usar PostgreSQL:

```
POSTGRES_DB=cotizaciones
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Grupos y permisos

El comando `python manage.py setup_groups` crea los grupos:

- Admin: todo
- Ventas: CRUD sin delete
- Solo_lectura: solo ver

Asigna usuarios a grupos desde el admin de Django.

## Datos de ejemplo

```bash
python manage.py seed_sample
```

## PDF (WeasyPrint)

WeasyPrint requiere dependencias del sistema. En Windows puede ser necesario:

- Instalar Visual C++ Build Tools
- Instalar GTK o los binarios de WeasyPrint según la guía oficial

Guía oficial: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows

## PDF – Datos de empresa

Los datos de la empresa en el PDF (nombre, RFC, dirección, teléfono, etc.) se leen de `settings.QUOTE_PDF_COMPANY`, que a su vez puede sobreescribirse con variables de entorno:

- `QUOTE_PDF_COMPANY_NAME`
- `QUOTE_PDF_COMPANY_WEBSITE`
- `QUOTE_PDF_COMPANY_STREET`
- `QUOTE_PDF_COMPANY_COLONY`
- `QUOTE_PDF_COMPANY_POSTAL_CODE`
- `QUOTE_PDF_COMPANY_PHONE`
- `QUOTE_PDF_COMPANY_MOBILE`
- `QUOTE_PDF_COMPANY_RFC`
- `QUOTE_PDF_COMPANY_EMAIL`

## Comandos útiles

- Crear migraciones: `python manage.py makemigrations`
- Aplicar migraciones: `python manage.py migrate`
- Superusuario: `python manage.py createsuperuser`

## Estructura

Apps:

- `customers`: clientes y contactos
- `catalog`: modelos de cámaras
- `quotes`: cotizaciones y items
