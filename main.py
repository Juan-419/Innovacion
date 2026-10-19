from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

from database import init_db
import models

# Routers
from routers import finca
from routers import ganado
from routers import tipo_animal
from routers import panel
from fastapi.staticfiles import StaticFiles


# Crear tablas en la base de datos
init_db()

app = FastAPI(
    title="Sistema de Gestión de Ganado",
    description="API para administrar fincas, ganado y tipos de ganado",
    version="1.0.0"
)


app.mount("/static", StaticFiles(directory="static"), name="static")

#---Templates---
templates = Jinja2Templates(directory="templates")

#---Statics---
app.mount("/static", StaticFiles(directory="static"), name="static")



# ============================================================
#                      CORS (opcional)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # En producción debes especificar dominio
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#                    RUTAS (Routers)
# ============================================================
app.include_router(finca.router)
app.include_router(ganado.router)
app.include_router(tipo_animal.router)
app.include_router(panel.router)  # inicio (panel) y alertas
