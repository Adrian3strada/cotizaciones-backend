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

## Despliegue en Railway

La app está preparada para desplegarse en [Railway](https://railway.app).

### 1. Crear proyecto en Railway

- Entra a [railway.app/new](https://railway.app/new)
- Elige **Deploy from GitHub repo** y conecta tu repositorio
- O usa la CLI: `railway init` y luego `railway up`

### 2. Añadir PostgreSQL

- En el proyecto, clic en **+ New** → **Database** → **PostgreSQL**
- Railway creará la base de datos automáticamente

### 3. Variables de entorno

En el servicio de la app, ve a **Variables** y añade:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY` | Una clave secreta segura (genera una nueva para producción) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` (o tu dominio específico) |

> **Nota:** Reemplaza `Postgres` por el nombre de tu servicio PostgreSQL si es diferente.

### 4. Comando Pre-Deploy (migraciones)

En **Settings** → **Deploy** → **Pre-Deploy Command**, añade:

```
python manage.py migrate --noinput
```

### 5. Dominio público

- En **Settings** → **Networking** → **Generate Domain**
- Railway asignará una URL como `tu-app.up.railway.app`

### 6. Superusuario (primera vez)

Tras el primer deploy, ejecuta en la terminal (con Railway CLI vinculado):

```bash
railway run python manage.py createsuperuser
railway run python manage.py setup_groups
```

---

## Despliegue en producción (general)

- **ALLOWED_HOSTS**: en `.env` define tu dominio, ej. `ALLOWED_HOSTS=midominio.com,www.midominio.com`
- **CSRF_TRUSTED_ORIGINS**: si usas HTTPS, añade `CSRF_TRUSTED_ORIGINS=https://midominio.com`
- **DEBUG**: debe ser `False` en producción (ya está en tu `.env`)
- **Archivos MEDIA**: con `DEBUG=False`, Django no sirve archivos subidos. Configura tu servidor web (Nginx/Apache) o un CDN para servir la carpeta `media/`.

## API REST

Endpoints para integración con ERP/CRM (requiere autenticación):

- `GET /api/quotes/` – Lista de cotizaciones (filtros: status, currency, customer, sales_user)
- `GET /api/quotes/<id>/` – Detalle de cotización con items
- `GET /api/customers/` – Lista de clientes
- `GET /api/catalog/` – Catálogo de modelos de cámara

Autenticación: sesión web o Basic Auth.

## Estructura

Apps:

- `customers`: clientes y contactos
- `catalog`: modelos de cámaras
- `quotes`: cotizaciones y items
- `api`: API REST
