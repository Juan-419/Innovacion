from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import date
from fastapi import UploadFile, File

# GanadoCreate se mantiene igual, sin la foto

#------Finca----

class FincaBase(BaseModel):
    nombre: str
    tamaño: int #Tamaño como entero (hectareas)
    ubicacion: str

class FincaCreate(FincaBase):
    pass

class Finca(FincaBase):
    id: int
    class Config:
        orm_mode = True


#-------Ganado------
class GanadoBase(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    edad: int
    sexo: str
    finca_id: int
    tipo_animal_id: int     #relación con TipoAnimal

class GanadoCreate(GanadoBase):
    pass

class Ganado(GanadoBase):
    id: int
    foto: Optional[str] = None
    estado: str = "Activo"
    fecha_estado: Optional[date] = None
    class Config:
        orm_mode = True

class GanadoUpdate(BaseModel):
    nombre: str | None = None
    edad: int | None = None
    sexo: str | None = None
    finca_id: int | None = None

    class Config:
        orm_mode = True


class GanadoUpdateData(BaseModel):
    identificacion: str
    nombre: Optional[str] = None
    fecha_nacimiento: date
    sexo: str
    finca_id: int
    tipo_animal_id: int

#-------Tipo de Animal------

class TipoAnimalBase(BaseModel):
    nombre: str

class TipoAnimalCreate(TipoAnimalBase):
    pass

class TipoAnimal(TipoAnimalBase):
    id: int

    class Config:
        from_attributes = True


#-------Eventos del animal (historial)------
ESTADOS = ("Activo", "Vendido", "Muerto")

class EstadoUpdate(BaseModel):
    estado: Literal[ESTADOS]
    fecha: Optional[date] = None

TIPOS_EVENTO = ("Vacuna", "Peso", "Tratamiento", "Reproducción", "Alimentación", "Otro")

class EventoCreate(BaseModel):
    tipo: Literal[TIPOS_EVENTO]
    fecha: date
    valor: Optional[float] = Field(None, ge=0)          # peso en kg, dosis, etc.
    descripcion: Optional[str] = Field(None, max_length=300)
    proxima_fecha: Optional[date] = None               # cuándo toca repetirlo

class Evento(EventoCreate):
    id: int
    ganado_id: int
    atendido: bool = False
    model_config = ConfigDict(from_attributes=True)
