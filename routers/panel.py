from datetime import date, timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload

import models
from database import get_db

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Panel"])


def pendientes_activos(db: Session):
    """Eventos con próxima fecha aún no atendidos, de animales activos, del más urgente al menos."""
    return (
        db.query(models.EventoGanado)
        .join(models.Ganado, models.EventoGanado.ganado_id == models.Ganado.id)
        .options(joinedload(models.EventoGanado.ganado))
        .filter(
            models.EventoGanado.proxima_fecha.isnot(None),
            models.EventoGanado.atendido.is_(False),
            models.Ganado.estado == "Activo",
        )
        .order_by(models.EventoGanado.proxima_fecha, models.EventoGanado.id)
        .all()
    )


def agrupar_alertas(pendientes, hoy: date):
    semana = hoy + timedelta(days=7)
    mes = hoy + timedelta(days=30)
    return {
        "vencidas": [e for e in pendientes if e.proxima_fecha < hoy],
        "semana": [e for e in pendientes if hoy <= e.proxima_fecha <= semana],
        "mes": [e for e in pendientes if semana < e.proxima_fecha <= mes],
        "despues": [e for e in pendientes if e.proxima_fecha > mes],
    }


# ============================================================
#                 INICIO = PANEL DE CONTROL
# ============================================================
@router.get("/")
def inicio(request: Request, db: Session = Depends(get_db)):
    hoy = date.today()
    G = models.Ganado

    por_estado = dict(db.query(G.estado, func.count(G.id)).group_by(G.estado).all())
    activos = por_estado.get("Activo", 0)

    por_finca = (
        db.query(models.Finca.nombre, func.count(G.id))
        .outerjoin(G, and_(G.finca_id == models.Finca.id, G.estado == "Activo"))
        .group_by(models.Finca.id, models.Finca.nombre)
        .order_by(models.Finca.nombre)
        .all()
    )
    por_tipo = (
        db.query(models.TipoAnimal.nombre, func.count(G.id))
        .join(G, G.tipo_animal_id == models.TipoAnimal.id)
        .filter(G.estado == "Activo")
        .group_by(models.TipoAnimal.id, models.TipoAnimal.nombre)
        .order_by(func.count(G.id).desc())
        .all()
    )
    por_sexo = (
        db.query(G.sexo, func.count(G.id)).filter(G.estado == "Activo").group_by(G.sexo).all()
    )
    sin_historial = db.query(func.count(G.id)).filter(G.estado == "Activo", ~G.eventos.any()).scalar() or 0

    alertas = agrupar_alertas(pendientes_activos(db), hoy)
    ultimos = (
        db.query(models.EventoGanado)
        .options(joinedload(models.EventoGanado.ganado))
        .order_by(models.EventoGanado.fecha_registro.desc(), models.EventoGanado.id.desc())
        .limit(6)
        .all()
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hoy": hoy.isoformat(),
            "activos": activos,
            "vendidos": por_estado.get("Vendido", 0),
            "muertos": por_estado.get("Muerto", 0),
            "total_fincas": db.query(func.count(models.Finca.id)).scalar() or 0,
            "por_finca": por_finca,
            "por_tipo": por_tipo,
            "por_sexo": por_sexo,
            "sin_historial": sin_historial,
            "alertas": alertas,
            "ultimos": ultimos,
        },
    )


# ============================================================
#                      ALERTAS PENDIENTES
# ============================================================
@router.get("/alertas")
def alertas_view(request: Request, db: Session = Depends(get_db)):
    hoy = date.today()
    return templates.TemplateResponse(
        "alertas.html",
        {"request": request, "hoy": hoy.isoformat(), "alertas": agrupar_alertas(pendientes_activos(db), hoy)},
    )
