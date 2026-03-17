# Migrar datos locales a producción (Railway)

Tu base de datos **local** (SQLite) y la de **producción** (PostgreSQL en Railway) son distintas. Los datos no se pierden al desplegar; simplemente nunca estuvieron en producción.

## Opción 1: Exportar e importar (recomendado)

### Paso 1: Exportar desde tu máquina local

En tu proyecto, con la base de datos local cargada:

```bash
python scripts/export_data.py
```

Esto crea `data_export.json` con clientes, contactos, cotizaciones, catálogo, etc. (sin usuarios, para no sobrescribir el superusuario de prod).

### Paso 2: Importar en Railway

**Opción A – Con Railway CLI:**

```bash
# Instala Railway CLI si no lo tienes: npm i -g @railway/cli
railway link   # vincula tu proyecto
railway run python manage.py loaddata data_export.json
```

**Opción B – Desde el panel de Railway:**

1. Entra a tu proyecto en Railway.
2. Abre la consola del servicio (o usa "Run Command").
3. Sube `data_export.json` al contenedor (o usa un volumen temporal).
4. Ejecuta: `python manage.py loaddata data_export.json`

**Opción C – Variable de entorno (para archivos pequeños):**

1. Convierte el JSON a una sola línea y guárdalo en una variable.
2. En Railway, crea una variable `DATA_FIXTURE` con ese contenido.
3. En el script de inicio, antes de gunicorn, añade algo como:
   ```bash
   echo "$DATA_FIXTURE" > data_export.json && python manage.py loaddata data_export.json
   ```

## Opción 2: Volver a cargar datos de prueba

Si solo necesitas datos de ejemplo:

```bash
railway run python manage.py seed_customers
railway run python manage.py seed_sample
```

(Usa los comandos `seed_*` que tengas en el proyecto.)

## Resumen

| Dónde      | Base de datos | Datos                          |
|------------|---------------|--------------------------------|
| Local      | SQLite        | Tus clientes, cotizaciones, etc. |
| Railway    | PostgreSQL    | Vacía hasta que importes       |

Los despliegues no borran datos de producción. Si ves la app vacía, es porque la base de datos de Railway empieza vacía y hay que importar los datos una vez.
