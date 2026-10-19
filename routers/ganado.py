import io
import os
import uuid
from datetime import date

import qrcode
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models, schemas
from database import get_db

templates = Jinja2Templates(directory="templates")

router = APIRouter(
    prefix="/ganado",
    tags=["Ganado"]
)

UPLOAD_DIR = "static/uploads"
EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FOTO_BYTES = 5 * 1024 * 1024  # 5 MB


# ============================================================
#                       FUNCIONES AUXILIARES
# ============================================================
def calcular_edad_meses(fecha_nacimiento: date) -> int:
    """La edad se calcula desde la fecha de nacimiento (ya no se digita)."""
    hoy = date.today()
    meses = (hoy.year - fecha_nacimiento.year) * 12 + (hoy.month - fecha_nacimiento.month)
    if hoy.day < fecha_nacimiento.day:
        meses -= 1
    return max(meses, 0)


async def guardar_foto(foto: UploadFile | None) -> str | None:
    """Guarda la foto con nombre aleatorio y valida tipo y tamaño."""
    if foto is None or not foto.filename:
        return None
    ext = os.path.splitext(foto.filename)[1].lower()
    if ext not in EXTENSIONES_FOTO or not (foto.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="La foto debe ser una imagen (jpg, png, webp o gif).")
    contenido = await foto.read()
    if not contenido:
        return None
    if len(contenido) > MAX_FOTO_BYTES:
        raise HTTPException(status_code=400, detail="La foto supera el tamaño máximo de 5 MB.")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ruta = f"{UPLOAD_DIR}/{uuid.uuid4().hex}{ext}"
    with open(ruta, "wb") as f:
        f.write(contenido)
    return ruta


def borrar_foto(ruta: str | None) -> None:
    if ruta and ruta.startswith(UPLOAD_DIR + "/") and os.path.isfile(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass


def url_ficha(request: Request, ganado_id: int) -> str:
    """URL pública de la ficha. En producción define PUBLIC_BASE_URL (ej. https://hato.onrender.com)."""
    base = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/ganado/detalle/{ganado_id}"


def _a_int(valor: str) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


# ============================================================
#                       VISTAS HTML
# ============================================================
# FORMULARIO HTML
@router.get("/registrar")
async def registrar_ganado_view(request: Request, db: Session = Depends(get_db)):
    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()
    return templates.TemplateResponse(
        "ganado/registrar_ganado.html",
        {"request": request, "fincas": fincas, "tipos_animales": tipos_animales}
    )


# Lista de ganado con búsqueda por identificación/nombre y filtro por finca
@router.get("/lista")
async def listar_ganado_view(request: Request, q: str = "", finca_id: str = "", estado: str = "Activo", db: Session = Depends(get_db)):
    consulta = db.query(models.Ganado)
    if estado in schemas.ESTADOS:          # "Todos" no filtra
        consulta = consulta.filter(models.Ganado.estado == estado)
    q = q.strip()
    if q:
        patron = f"%{q}%"
        consulta = consulta.filter(or_(
            models.Ganado.identificacion.ilike(patron),
            models.Ganado.nombre.ilike(patron),
        ))
    finca_sel = _a_int(finca_id)
    if finca_sel:
        consulta = consulta.filter(models.Ganado.finca_id == finca_sel)
    ganados = consulta.order_by(models.Ganado.identificacion).all()
    fincas = db.query(models.Finca).order_by(models.Finca.nombre).all()
    return templates.TemplateResponse(
        "ganado/lista_ganado.html",
        {"request": request, "ganados": ganados, "fincas": fincas, "q": q, "finca_sel": finca_sel,
         "estado_sel": estado, "estados": schemas.ESTADOS}
    )


# Hoja de etiquetas QR imprimible
@router.get("/etiquetas")
async def etiquetas_view(request: Request, finca_id: str = "", db: Session = Depends(get_db)):
    consulta = db.query(models.Ganado).filter(models.Ganado.estado == "Activo")
    finca_sel = _a_int(finca_id)
    if finca_sel:
        consulta = consulta.filter(models.Ganado.finca_id == finca_sel)
    ganados = consulta.order_by(models.Ganado.identificacion).all()
    fincas = db.query(models.Finca).order_by(models.Finca.nombre).all()
    return templates.TemplateResponse(
        "ganado/etiquetas.html",
        {"request": request, "ganados": ganados, "fincas": fincas, "finca_sel": finca_sel}
    )


# Muestra el formulario para editar Ganado (precargado)
# URL: /ganado/editar/{ganado_id}
@router.get("/editar/{ganado_id}")
async def editar_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    """Muestra el formulario de edición, precargando datos y listas de opciones."""
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    fincas = db.query(models.Finca).all()
    tipos_animales = db.query(models.TipoAnimal).all()

    return templates.TemplateResponse(
        "ganado/editar_ganado.html",
        {
            "request": request,
            "ganado": ganado,
            "fincas": fincas,
            "tipos_animales": tipos_animales
        }
    )


# Detalle de un animal (ficha + historial + QR)
# URL: /ganado/detalle/{ganado_id}
@router.get("/detalle/{ganado_id}")
async def detalle_ganado_view(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    """Muestra la ficha de un animal con su historial."""
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    # eventos ya vienen ordenados del más reciente al más antiguo
    ultimo_peso = next((e for e in ganado.eventos if e.tipo == "Peso" and e.valor), None)
    ultima_vacuna = next((e for e in ganado.eventos if e.tipo == "Vacuna"), None)

    return templates.TemplateResponse(
        "ganado/detalle_ganado.html",
        {
            "request": request,
            "ganado": ganado,
            "edad_meses": calcular_edad_meses(ganado.fecha_nacimiento) if ganado.fecha_nacimiento else ganado.edad,
            "tipos_evento": schemas.TIPOS_EVENTO,
            "hoy": date.today().isoformat(),
            "ultimo_peso": ultimo_peso,
            "ultima_vacuna": ultima_vacuna,
            "estados": schemas.ESTADOS,
            "pendientes": sorted([e for e in ganado.eventos if e.proxima_fecha and not e.atendido], key=lambda e: e.proxima_fecha),
            "ficha_url": url_ficha(request, ganado.id),
        }
    )


# Imagen QR de la ficha
# URL: /ganado/{ganado_id}/qr.png
@router.get("/{ganado_id}/qr.png")
def qr_ganado(ganado_id: int, request: Request, db: Session = Depends(get_db)):
    existe = db.query(models.Ganado.id).filter(models.Ganado.id == ganado_id).first()
    if not existe:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    img = qrcode.make(url_ficha(request, ganado_id), box_size=8, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


# ============================================================
#                   RUTAS DE LA API (CRUD)
# ============================================================
# Crear ganado (formulario con foto) - URL: POST /ganado/api/
@router.post("/api/", response_model=schemas.Ganado)
async def crear_ganado(
    identificacion: str = Form(...),
    nombre: str | None = Form(None),
    fecha_nacimiento: date = Form(...),
    sexo: str = Form(...),
    edad: int | None = Form(None),  # ya no es necesaria: se calcula
    finca_id: int = Form(...),
    tipo_animal_id: int = Form(...),
    foto: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    identificacion = identificacion.strip()
    if not identificacion:
        raise HTTPException(status_code=400, detail="La identificación es obligatoria.")
    if fecha_nacimiento > date.today():
        raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura.")
    if db.query(models.Ganado).filter(models.Ganado.identificacion == identificacion).first():
        raise HTTPException(status_code=400, detail=f"Ya existe un animal con la identificación '{identificacion}'.")
    if not db.query(models.Finca).filter(models.Finca.id == finca_id).first():
        raise HTTPException(status_code=400, detail="La finca seleccionada no existe.")
    if not db.query(models.TipoAnimal).filter(models.TipoAnimal.id == tipo_animal_id).first():
        raise HTTPException(status_code=400, detail="El tipo de animal seleccionado no existe.")

    ruta_foto = await guardar_foto(foto)  # solo después de validar todo lo demás

    nuevo_ganado = models.Ganado(
        identificacion=identificacion,
        nombre=(nombre or "").strip() or None,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo,
        edad=calcular_edad_meses(fecha_nacimiento),
        finca_id=finca_id,
        tipo_animal_id=tipo_animal_id,
        foto=ruta_foto,
    )
    db.add(nuevo_ganado)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        borrar_foto(ruta_foto)
        raise HTTPException(status_code=400, detail=f"Ya existe un animal con la identificación '{identificacion}'.")
    db.refresh(nuevo_ganado)
    return nuevo_ganado


# Listar ganado (GET API) - URL: /ganado/api/
@router.get("/api/", response_model=list[schemas.Ganado])
def listar_ganado_api(db: Session = Depends(get_db)):
    return db.query(models.Ganado).all()


# Eliminar ganado (DELETE API) - URL: /ganado/api/{ganado_id}
@router.delete("/api/{ganado_id}")
def eliminar_ganado(ganado_id: int, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    foto = ganado.foto
    db.delete(ganado)  # borra también su historial (cascade)
    db.commit()
    borrar_foto(foto)
    return {"mensaje": "Ganado eliminado correctamente"}


# Actualizar (PUT) un registro de ganado - URL: /ganado/{ganado_id}
@router.put("/{ganado_id}", response_model=schemas.Ganado)
def actualizar_ganado(ganado_id: int, datos: schemas.GanadoUpdateData, db: Session = Depends(get_db)):
    ganado = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not ganado:
        raise HTTPException(status_code=404, detail="Registro de ganado no encontrado")

    if datos.fecha_nacimiento > date.today():
        raise HTTPException(status_code=400, detail="La fecha de nacimiento no puede ser futura.")
    if not db.query(models.Finca).filter(models.Finca.id == datos.finca_id).first():
        raise HTTPException(status_code=400, detail="La finca seleccionada no existe.")
    if not db.query(models.TipoAnimal).filter(models.TipoAnimal.id == datos.tipo_animal_id).first():
        raise HTTPException(status_code=400, detail="El tipo de animal seleccionado no existe.")

    for key, value in datos.model_dump().items():
        setattr(ganado, key, value)
    ganado.identificacion = (ganado.identificacion or "").strip()
    ganado.edad = calcular_edad_meses(ganado.fecha_nacimiento)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"La identificación '{datos.identificacion}' ya está en uso por otro animal."
        )

    db.refresh(ganado)
    return ganado


# ============================================================
#              HISTORIAL DEL ANIMAL (VACUNAS, PESO, ETC.)
# ============================================================
@router.post("/{ganado_id}/eventos", response_model=schemas.Evento, status_code=201)
def crear_evento(ganado_id: int, datos: schemas.EventoCreate, db: Session = Depends(get_db)):
    animal = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")

    descripcion = (datos.descripcion or "").strip() or None
    if datos.tipo == "Peso" and not datos.valor:
        raise HTTPException(status_code=400, detail="Indica el peso en kg (mayor a 0).")
    if datos.tipo in ("Vacuna", "Tratamiento") and not descripcion:
        raise HTTPException(status_code=400, detail=f"Indica el nombre de la {datos.tipo.lower()}.")

    if datos.proxima_fecha and datos.proxima_fecha < datos.fecha:
        raise HTTPException(status_code=400, detail="La próxima fecha no puede ser anterior a la fecha del evento.")

    # Si ya existía una alerta pendiente del mismo tipo y detalle (p. ej. el refuerzo de la misma
    # vacuna), registrar este evento la da por atendida.
    mismo_detalle = (
        func.lower(models.EventoGanado.descripcion) == descripcion.lower()
        if descripcion else models.EventoGanado.descripcion.is_(None)
    )
    previas = db.query(models.EventoGanado).filter(
        models.EventoGanado.ganado_id == ganado_id,
        models.EventoGanado.tipo == datos.tipo,
        models.EventoGanado.proxima_fecha.isnot(None),
        models.EventoGanado.atendido.is_(False),
        mismo_detalle,
    ).all()
    for previa in previas:
        previa.atendido = True

    evento = models.EventoGanado(
        ganado_id=ganado_id,
        tipo=datos.tipo,
        fecha=datos.fecha,
        valor=datos.valor,
        descripcion=descripcion,
        proxima_fecha=datos.proxima_fecha,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.delete("/eventos/{evento_id}")
def eliminar_evento(evento_id: int, db: Session = Depends(get_db)):
    evento = db.query(models.EventoGanado).filter(models.EventoGanado.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(evento)
    db.commit()
    return {"mensaje": "Evento eliminado correctamente"}


@router.post("/eventos/{evento_id}/atendido")
def marcar_atendido(evento_id: int, db: Session = Depends(get_db)):
    """Marca como hecha una alerta pendiente (sin crear un evento nuevo)."""
    evento = db.query(models.EventoGanado).filter(models.EventoGanado.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    evento.atendido = True
    db.commit()
    return {"mensaje": "Alerta marcada como atendida"}


# ============================================================
#              ESTADO DEL ANIMAL (ACTIVO / VENDIDO / MUERTO)
# ============================================================
@router.put("/{ganado_id}/estado", response_model=schemas.Ganado)
def cambiar_estado(ganado_id: int, datos: schemas.EstadoUpdate, db: Session = Depends(get_db)):
    """Cambia el estado conservando todo el historial (en vez de eliminar el animal)."""
    animal = db.query(models.Ganado).filter(models.Ganado.id == ganado_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Ganado no encontrado")
    if datos.fecha and datos.fecha > date.today():
        raise HTTPException(status_code=400, detail="La fecha del cambio de estado no puede ser futura.")

    animal.estado = datos.estado
    animal.fecha_estado = None if datos.estado == "Activo" else (datos.fecha or date.today())
    db.commit()
    db.refresh(animal)
    return animal
