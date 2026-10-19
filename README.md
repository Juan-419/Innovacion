# Hato App

Gestión de fincas y ganado (FastAPI + SQLAlchemy + Jinja2).

## Ejecutar
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
La tabla nueva (`eventos_ganado`) se crea sola al iniciar; no hace falta tocar la base de datos existente.

## Novedades de esta versión
- **Panel de inicio:** animales activos, por finca/tipo/sexo, alertas vencidas y de la semana, últimos eventos y activos sin historial.
- **Estado del animal (Activo / Vendido / Muerto):** el historial se conserva; los no activos salen de la lista, las etiquetas y las alertas.
- **Próxima fecha y alertas (`/alertas`):** los eventos pueden tener próxima fecha (refuerzo, control). Registrar el mismo evento (misma vacuna o tratamiento) cierra la alerta; también se puede marcar como hecha.
- **Migración automática:** al iniciar se agregan las columnas nuevas a bases existentes (`estado`, `fecha_estado`, `proxima_fecha`, `atendido`).
- **Base de datos configurable:** variable `DATABASE_URL` (Postgres/Supabase); sin ella usa SQLite local.

### Versión anterior
- **Historial por animal:** vacunas, pesos, tratamientos, reproducción, alimentación y otros, con resumen (último peso, última vacuna) en la ficha.
- **Código QR por animal** (`/ganado/{id}/qr.png`) y **hoja de etiquetas imprimible** (`/ganado/etiquetas`).
- **Búsqueda** por identificación o nombre y filtro por finca en `/ganado/lista`.
- **Duplicados:** mensaje claro al registrar o editar con una identificación repetida.
- **Edad** calculada automáticamente desde la fecha de nacimiento.
- **Fotos** guardadas con nombre aleatorio, validadas (imagen, máx. 5 MB) y borradas al eliminar el animal.
- Corregido: `IntegrityError` sin importar, ruta POST duplicada, botón "Eliminar" de la ficha (apuntaba a una ruta inexistente) y CORS.

## Producción (Render, Web Service)
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- `PUBLIC_BASE_URL`: URL pública (ej. `https://hato.onrender.com`) para que el QR apunte al dominio correcto.
- `DATABASE_URL`: cadena de Postgres/Supabase. Sin ella usa SQLite, que se borra en cada redeploy en Render.
- Las fotos se guardan en disco local (`static/uploads`) y también se pierden al redeploy salvo que uses un disco persistente o almacenamiento externo.

## Pendiente
Modo sin conexión con sincronización (PWA) y usuarios/login.
