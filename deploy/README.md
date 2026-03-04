# Despliegue en Contabo (Ubuntu)

Guía para desplegar la aplicación Cotizaciones en un VPS de Contabo con Ubuntu 22.04.

## Requisitos previos

- VPS Contabo con Ubuntu 22.04
- Acceso SSH como root o con sudo
- Dominio apuntando al servidor (opcional; también puedes usar la IP)

## Despliegue inicial

### 1. Conectarte al servidor

```bash
ssh root@tu-ip-contabo
```

### 2. Clonar el repositorio (o subir el código)

```bash
git clone https://github.com/tu-org/cotizaciones_project.git /var/www/cotizaciones
```

### 3. Ejecutar el script de configuración

Define las variables y ejecuta el script:

```bash
export REPO_URL="https://github.com/tu-org/cotizaciones_project.git"
export DOMAIN="cotizaciones.tudominio.com"   # o la IP: 123.45.67.89
export DB_PASS="contraseña_segura_postgres"

cd /var/www/cotizaciones
chmod +x deploy/ubuntu-setup.sh
sudo ./deploy/ubuntu-setup.sh
```

Si el repo ya está clonado, puedes omitir `REPO_URL` y el script usará el directorio actual.

### 4. Configurar el archivo .env

Edita `/var/www/cotizaciones/.env` con los valores reales:

```bash
nano /var/www/cotizaciones/.env
```

Variables importantes:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django (50+ caracteres) |
| `DEBUG` | `False` en producción |
| `CONTABO_DOMAIN` | Tu dominio o IP |
| `DATABASE_URL` | `postgresql://usuario:password@localhost:5432/cotizaciones_db` |
| `DJANGO_SUPERUSER_*` | Para crear el primer admin |

### 5. SSL con Let's Encrypt (recomendado)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d cotizaciones.tudominio.com
```

## Actualizar la aplicación

Después del despliegue inicial, para actualizar:

```bash
cd /var/www/cotizaciones
git pull
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart cotizaciones
```

O usa el script de actualización:

```bash
./deploy/update.sh
```

## Comandos útiles

| Comando | Descripción |
|---------|-------------|
| `sudo systemctl status cotizaciones` | Estado del servicio |
| `sudo systemctl restart cotizaciones` | Reiniciar la app |
| `journalctl -u cotizaciones -f` | Ver logs en tiempo real |
| `sudo systemctl reload nginx` | Recargar Nginx |

## Variables de entorno para Contabo

En `.env` o en el servicio systemd:

- `CONTABO_DOMAIN`: Dominio o IP (se añade a ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS)
- `DATABASE_SSL_MODE`: `disable` si PostgreSQL está en localhost (por defecto se detecta)
- `ALLOWED_HOSTS`: Lista separada por comas si necesitas varios dominios
