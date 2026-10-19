import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Por defecto usa SQLite local. En producción define DATABASE_URL (ej. la cadena de Postgres/Supabase).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ganaderia.db").strip()
if DATABASE_URL.startswith("postgres://"):  # Render/Heroku entregan este prefijo antiguo
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Columnas agregadas después de la primera versión. create_all() solo crea tablas
# nuevas, no agrega columnas a tablas que ya existen, así que las añadimos aquí.
COLUMNAS_NUEVAS = {
    "ganados": [
        ("estado", "VARCHAR(20) NOT NULL DEFAULT 'Activo'"),
        ("fecha_estado", "DATE"),
    ],
    "eventos_ganado": [
        ("proxima_fecha", "DATE"),
        ("atendido", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ],
}


def asegurar_columnas() -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for tabla, columnas in COLUMNAS_NUEVAS.items():
            if not insp.has_table(tabla):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabla)}
            for nombre, definicion in columnas:
                if nombre not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"))


def init_db() -> None:
    """Crea tablas faltantes y agrega columnas nuevas a bases existentes."""
    import models  # noqa: F401  (registra los modelos en Base)
    Base.metadata.create_all(bind=engine)
    asegurar_columnas()


# Dependencia para obtener sesión
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
