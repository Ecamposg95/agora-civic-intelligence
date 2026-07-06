from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MilitanteCreate(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=255)
    consentimiento: bool
    curp: Optional[str] = Field(default=None, max_length=18)
    clave_elector: Optional[str] = Field(default=None, max_length=18)
    sexo: Optional[str] = Field(default=None, pattern="^[MF]$")
    fecha_nacimiento: Optional[date] = None
    seccion: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=160)
    telefono: Optional[str] = Field(default=None, max_length=40)
    calle_numero: Optional[str] = Field(default=None, max_length=500)
    colonia: Optional[str] = Field(default=None, max_length=255)
    cp: Optional[str] = Field(default=None, max_length=10)
    municipio: Optional[str] = Field(default=None, max_length=120)
    estado_domicilio: Optional[str] = Field(default=None, max_length=120)
    es_activista: bool = False
    estructura: Optional[str] = Field(default=None, max_length=120)
    promotor: Optional[str] = Field(default=None, max_length=160)
    folio_externo: Optional[str] = Field(default=None, max_length=60)
    fecha_afiliacion: Optional[date] = None
    client_uuid: Optional[str] = Field(default=None, max_length=64)
    lat: Optional[float] = None
    lng: Optional[float] = None


class MilitanteRead(BaseModel):
    id: str
    folio: str
    nombre_completo: str
    seccion: Optional[str] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    colonia: Optional[str] = None
    municipio: Optional[str] = None
    es_activista: bool
    estructura: Optional[str] = None
    curp_masked: Optional[str] = None
    clave_masked: Optional[str] = None
    estado: str
    quality_flags: Optional[dict] = None
    activista_nombre: Optional[str] = None
    tiene_frente: bool = False
    tiene_reverso: bool = False
    tiene_firma: bool = False
    fecha_afiliacion: Optional[date] = None
    created_at: datetime


class MilitanteList(BaseModel):
    items: list[MilitanteRead]
    total: int
    limit: int
    offset: int
    has_territory: bool = True


class MilitanteEstadoUpdate(BaseModel):
    estado: str = Field(pattern="^(VALIDADO|OBSERVADO)$")
    observacion_validacion: Optional[str] = Field(default=None, max_length=500)


class MilitanteReveal(BaseModel):
    curp: Optional[str] = None
    clave_elector: Optional[str] = None
    frente_url: Optional[str] = None
    reverso_url: Optional[str] = None
    firma_url: Optional[str] = None


class PanoramaKpis(BaseModel):
    total: int
    validados: int
    observados: int
    registrados: int
    meta: Optional[int] = None
    ritmo_7d: int
    ritmo_30d: int


class PanoramaSeccion(BaseModel):
    seccion: str
    militantes: int
    lista_nominal: Optional[int] = None
    prioridad: Optional[str] = None
    promovidos: int = 0


class PanoramaActivista(BaseModel):
    activista_id: Optional[str] = None
    nombre: str
    militantes: int
    con_banderas: int


class MilitantePanorama(BaseModel):
    kpis: PanoramaKpis
    por_seccion: list[PanoramaSeccion]
    por_activista: list[PanoramaActivista]
    trend: list[int]  # last 14 days count
