#!/bin/bash
# =============================================================================
# Script de despliegue para Cotizaciones en Contabo (Ubuntu 22.04)
# Ejecutar como root o con sudo
# =============================================================================

set -e

APP_USER="${APP_USER:-cotizaciones}"
APP_DIR="${APP_DIR:-/var/www/cotizaciones}"
REPO_URL="${REPO_URL:-}"  # URL del repo git (ej: https://github.com/tu-org/cotizaciones_project.git)
DOMAIN="${DOMAIN:-}"     # Dominio o IP (ej: cotizaciones.tudominio.com)
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

# -----------------------------------------------------------------------------
# 1. Actualizar sistema e instalar dependencias
# -----------------------------------------------------------------------------
echo ">>> Actualizando sistema..."
apt update && apt upgrade -y

echo ">>> Instalando dependencias..."
apt install -y \
    python3 python3-pip python3-venv \
    postgresql postgresql-contrib \
    nginx \
    git \
    libpq-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    libcairo2 libgirepository1.0-dev

# -----------------------------------------------------------------------------
# 2. Crear usuario y directorio de la app
# -----------------------------------------------------------------------------
if ! id "$APP_USER" &>/dev/null; then
    echo ">>> Creando usuario $APP_USER..."
    useradd -m -s /bin/bash "$APP_USER"
fi

mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# -----------------------------------------------------------------------------
# 3. Configurar PostgreSQL
# -----------------------------------------------------------------------------
echo ">>> Configurando PostgreSQL..."
DB_NAME="${DB_NAME:-cotizaciones_db}"
DB_USER="${DB_USER:-cotizaciones_user}"
DB_PASS="${DB_PASS:-}"  # ¡IMPORTANTE! Definir antes de ejecutar

if [ -z "$DB_PASS" ]; then
    echo "ADVERTENCIA: DB_PASS no está definido. Genera una contraseña y ejecuta:"
    echo "  sudo -u postgres psql -c \"CREATE USER $DB_USER WITH PASSWORD 'tu_password';\""
    echo "  sudo -u postgres psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\""
else
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# 4. Clonar o actualizar repositorio
# -----------------------------------------------------------------------------
if [ -n "$REPO_URL" ]; then
    echo ">>> Clonando repositorio..."
    if [ -d "$APP_DIR/.git" ]; then
        su - "$APP_USER" -c "cd $APP_DIR && git pull"
    else
        su - "$APP_USER" -c "git clone $REPO_URL $APP_DIR"
    fi
else
    echo ">>> REPO_URL no definido. Clona manualmente el repo en $APP_DIR"
fi

# -----------------------------------------------------------------------------
# 5. Entorno virtual y dependencias Python
# -----------------------------------------------------------------------------
echo ">>> Configurando entorno Python..."
su - "$APP_USER" -c "cd $APP_DIR && python3 -m venv venv"
su - "$APP_USER" -c "cd $APP_DIR && ./venv/bin/pip install -r requirements.txt"
su - "$APP_USER" -c "cd $APP_DIR && ./venv/bin/python manage.py collectstatic --noinput"

# -----------------------------------------------------------------------------
# 6. Archivo .env (ejemplo)
# -----------------------------------------------------------------------------
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ">>> Creando archivo .env de ejemplo..."
    cat > "$ENV_FILE" << EOF
# Copia y edita con tus valores reales
DEBUG=False
SECRET_KEY=cambiar-por-una-clave-secreta-de-50-caracteres-minimo
ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN
CONTABO_DOMAIN=$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN

# PostgreSQL (local en Contabo)
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
# O usar variables separadas:
# POSTGRES_DB=$DB_NAME
# POSTGRES_USER=$DB_USER
# POSTGRES_PASSWORD=$DB_PASS
# POSTGRES_HOST=localhost

# Superusuario inicial (opcional)
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_PASSWORD=tu_password
# DJANGO_SUPERUSER_EMAIL=admin@tudominio.com
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo ">>> Edita $ENV_FILE con tus valores reales antes de continuar."
fi

# -----------------------------------------------------------------------------
# 7. Migraciones (cargar .env y ejecutar)
# -----------------------------------------------------------------------------
echo ">>> Ejecutando migraciones..."
if [ -f "$ENV_FILE" ]; then
    su "$APP_USER" -c "cd $APP_DIR && export \$(grep -v '^#' .env | xargs) && ./venv/bin/python manage.py migrate --noinput"
fi

# -----------------------------------------------------------------------------
# 8. Servicio systemd (usa scripts/start.py: migraciones + gunicorn)
# -----------------------------------------------------------------------------
echo ">>> Configurando servicio Gunicorn..."
cat > /etc/systemd/system/cotizaciones.service << EOF
[Unit]
Description=Cotizaciones Django Gunicorn
After=network.target postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/python scripts/start.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cotizaciones
systemctl start cotizaciones

# -----------------------------------------------------------------------------
# 9. Nginx
# -----------------------------------------------------------------------------
echo ">>> Configurando Nginx..."
cat > /etc/nginx/sites-available/cotizaciones << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /static/ {
        alias $APP_DIR/staticfiles/;
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/cotizaciones /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# -----------------------------------------------------------------------------
# 10. Certificado SSL (Let's Encrypt) - opcional
# -----------------------------------------------------------------------------
if [ -n "$DOMAIN" ] && [[ "$DOMAIN" != *[0-9]*.[0-9]*.[0-9]*.[0-9]* ]]; then
    echo ">>> Para instalar SSL con Let's Encrypt, ejecuta:"
    echo "  sudo apt install certbot python3-certbot-nginx -y"
    echo "  sudo certbot --nginx -d $DOMAIN"
fi

echo ""
echo "=============================================="
echo "Despliegue completado."
echo "App: http://$DOMAIN (o IP del servidor)"
echo "Servicio: systemctl status cotizaciones"
echo "Logs: journalctl -u cotizaciones -f"
echo "=============================================="
