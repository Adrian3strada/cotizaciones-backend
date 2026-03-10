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

## PDF – Imagen del encabezado (a la altura del logo)

La imagen que aparece en la esquina superior derecha del PDF, a la misma altura que el logo, se busca en `static/img/quote_header_right.png`. Coloca ahí tu imagen (ej: ilustración de proyectores/monitores).

Para usar otra ruta: `QUOTE_PDF_HEADER_IMAGE=img/mi_imagen.png`

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
| `ALLOWED_HOSTS` | Tu dominio (ej. `tu-app.up.railway.app`) o déjalo vacío para usar `RAILWAY_PUBLIC_DOMAIN` |

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

- **SECRET_KEY**: obligatorio en producción (`DEBUG=False`). Genera una con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- **ALLOWED_HOSTS**: en `.env` define tu dominio, ej. `ALLOWED_HOSTS=midominio.com,www.midominio.com`
- **CSRF_TRUSTED_ORIGINS**: si usas HTTPS, añade `CSRF_TRUSTED_ORIGINS=https://midominio.com`
- **DEBUG**: debe ser `False` en producción (ya está en tu `.env`)
- **Archivos MEDIA**: con `DEBUG=False`, Django no sirve archivos subidos. Configura Nginx (ver abajo) o un CDN para servir la carpeta `media/`.
- **NGROK_HOSTS** (solo dev): si usas ngrok, define `NGROK_HOSTS=abc123.ngrok-free.app` para permitir el túnel.

### Archivos MEDIA con Nginx

En tu bloque `server` de Nginx, añade:

```nginx
location /media/ {
    alias /var/www/cotizaciones/media/;
}
```

### Tareas programadas (cron)

Los comandos `expire_quotes` y `warn_expiring_quotes` deben ejecutarse periódicamente. Configura cron:

```bash
crontab -e
```

Añade (ajusta la ruta y el usuario):

```
# Expirar cotizaciones vencidas (diario a las 00:05)
5 0 * * * cd /var/www/cotizaciones && ./venv/bin/python manage.py expire_quotes

# Avisar cotizaciones por vencer (diario a las 08:00)
0 8 * * * cd /var/www/cotizaciones && ./venv/bin/python manage.py warn_expiring_quotes
```

## API REST

Endpoints para integración con ERP/CRM (requiere autenticación):

- `GET /api/quotes/` – Lista de cotizaciones (filtros: status, currency, customer, sales_user)
- `GET /api/quotes/<id>/` – Detalle de cotización con items
- `GET /api/customers/` – Lista de clientes
- `GET /api/catalog/` – Catálogo de modelos de cámara
- `POST /api/auth-token/` – Obtener token (body: `username`, `password`)

Autenticación: Token (recomendado para integraciones), sesión web o Basic Auth.

Documentación OpenAPI: `/api/schema/`, Swagger UI: `/api/schema/swagger-ui/`, ReDoc: `/api/schema/redoc/`

## Estructura

Apps:

- `customers`: clientes y contactos
- `catalog`: modelos de cámaras
- `quotes`: cotizaciones y items
- `api`: API REST
