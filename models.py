from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Float, Boolean, false
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Finca(Base):
    __tablename__ = "fincas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tamaño = Column(Integer, nullable=False)
    ubicacion = Column(String(200), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    ganados = relationship(
        "Ganado", 
        back_populates="finca",
        cascade="all, delete-orphan"
    )

class TipoAnimal(Base):
    __tablename__ = "tipos_animales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    ganados = relationship("Ganado", back_populates="tipo_animal")

class Ganado(Base):
    __tablename__ = "ganados"

    id = Column(Integer, primary_key=True, index=True)
    identificacion = Column(String, index=True, unique=True, nullable=False)
    nombre = Column(String(100), nullable=True)
    edad = Column(Integer, nullable=False)
    sexo = Column(String(10), nullable=False)
    fecha_nacimiento = Column(Date)
    finca_id = Column(Integer, ForeignKey("fincas.id"), nullable=False)
    tipo_animal_id = Column(Integer, ForeignKey("tipos_animales.id"), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    foto = Column(String, nullable=True)  
    estado = Column(String(20), nullable=False, default="Activo", server_default="Activo")  # Activo / Vendido / Muerto
    fecha_estado = Column(Date, nullable=True)


    finca = relationship("Finca", back_populates="ganados")
    tipo_animal = relationship("TipoAnimal", back_populates="ganados")
    eventos = relationship(
        "EventoGanado",
        back_populates="ganado",
        cascade="all, delete-orphan",
        order_by="[EventoGanado.fecha.desc(), EventoGanado.id.desc()]",
    )


class EventoGanado(Base):
    """Historial de cada animal: vacunas, pesos, tratamientos, etc."""
    __tablename__ = "eventos_ganado"

    id = Column(Integer, primary_key=True, index=True)
    ganado_id = Column(Integer, ForeignKey("ganados.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)       # Vacuna, Peso, Tratamiento...
    fecha = Column(Date, nullable=False)
    valor = Column(Float, nullable=True)            # p. ej. peso en kg
    descripcion = Column(String(300), nullable=True)
    proxima_fecha = Column(Date, nullable=True)      # próxima aplicación / refuerzo / control
    atendido = Column(Boolean, nullable=False, default=False, server_default=false())
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    ganado = relationship("Ganado", back_populates="eventos")
