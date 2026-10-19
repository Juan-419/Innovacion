# Hato App

Gestión de fincas y ganado (FastAPI + SQLAlchemy + Jinja2).

## Ejecutar
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
La tabla nueva (`eventos_ganado`) se crea sola al iniciar; no hace falta tocar la base de datos existente.

## Novedades de esta versión
- **Historial por animal:** vacunas, pesos, tratamientos, reproducción, alimentación y otros, con resumen (último peso, última vacuna) en la ficha.
- **Código QR por animal** (`/ganado/{id}/qr.png`) y **hoja de etiquetas imprimible** (`/ganado/etiquetas`).
- **Búsqueda** por identificación o nombre y filtro por finca en `/ganado/lista`.
- **Duplicados:** mensaje claro al registrar o editar con una identificación repetida.
- **Edad** calculada automáticamente desde la fecha de nacimiento.
- **Fotos** guardadas con nombre aleatorio, validadas (imagen, máx. 5 MB) y borradas al eliminar el animal.
- Corregido: `IntegrityError` sin importar, ruta POST duplicada, botón "Eliminar" de la ficha (apuntaba a una ruta inexistente) y CORS.

## Producción (Render)
Define la variable de entorno `PUBLIC_BASE_URL` con la URL pública (ej. `https://hato.onrender.com`) para que el QR apunte al dominio correcto.
SQLite y las fotos en disco se pierden en cada redeploy si no hay disco persistente; para uso real conviene PostgreSQL/Supabase y almacenamiento externo.

## Pendiente
Modo sin conexión con sincronización (PWA) y usuarios/login.
