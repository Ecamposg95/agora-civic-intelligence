"""/api/militantes — formal affiliation capture + coordinator panorama."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.dependencies import CampaignCtx, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.militante import (
    MilitanteCreate, MilitanteEstadoUpdate, MilitanteList, MilitantePanorama,
    MilitanteRead, MilitanteReveal,
)
from app.services import militante_service

router = APIRouter(tags=["militantes"])

_CAPTURE = Annotated[object, Depends(require_roles(
    UserRole.ACTIVISTA, UserRole.CAPTURISTA, UserRole.LIDER,
    UserRole.COORDINADOR, UserRole.ADMIN))]
_REVIEW = Annotated[object, Depends(require_roles(
    UserRole.COORDINADOR, UserRole.ADMIN))]

_MAX_DOC_BYTES = 6 * 1024 * 1024


@router.post("/militantes", response_model=MilitanteRead, status_code=status.HTTP_201_CREATED)
def create(db: DbSession, ctx: CampaignCtx, _p: _CAPTURE, data: MilitanteCreate):
    try:
        m = militante_service.create_militante(db, ctx, data)
    except militante_service.ConsentRequired:
        raise HTTPException(status_code=422, detail="Consentimiento requerido")
    except militante_service.NoActiveNotice:
        raise HTTPException(status_code=409, detail="No hay aviso de privacidad activo")
    m.activista_nombre = None
    m.tiene_frente = m.credencial_frente_key is not None
    m.tiene_reverso = m.credencial_reverso_key is not None
    m.tiene_firma = m.firma_key is not None
    return MilitanteRead.model_validate(m, from_attributes=True)


@router.get("/militantes", response_model=MilitanteList)
def list_(db: DbSession, ctx: CampaignCtx, _p: _CAPTURE,
          seccion: Annotated[Optional[str], Query()] = None,
          estado: Annotated[Optional[str], Query()] = None,
          activista: Annotated[Optional[str], Query()] = None,
          flag: Annotated[Optional[str], Query()] = None,
          q: Annotated[Optional[str], Query()] = None,
          limit: Annotated[int, Query(ge=1, le=200)] = 50,
          offset: Annotated[int, Query(ge=0)] = 0):
    rows, total, has_territory = militante_service.list_militantes(
        db, ctx, seccion=seccion, estado=estado, activista=activista,
        flag=flag, q=q, limit=limit, offset=offset)
    return MilitanteList(
        items=[MilitanteRead.model_validate(r, from_attributes=True) for r in rows],
        total=total, limit=limit, offset=offset, has_territory=has_territory)


@router.get("/militantes/panorama", response_model=MilitantePanorama)
def panorama(db: DbSession, ctx: CampaignCtx, _p: _REVIEW):
    return MilitantePanorama.model_validate(militante_service.panorama(db, ctx))


@router.get("/militantes/{mid}", response_model=MilitanteRead)
def get_one(db: DbSession, ctx: CampaignCtx, _p: _CAPTURE, mid: str):
    m = militante_service.get_militante(db, ctx, mid)
    if m is None:
        raise HTTPException(status_code=404, detail="Militante no encontrado")
    m.tiene_frente = m.credencial_frente_key is not None
    m.tiene_reverso = m.credencial_reverso_key is not None
    m.tiene_firma = m.firma_key is not None
    m.activista_nombre = None
    return MilitanteRead.model_validate(m, from_attributes=True)


@router.post("/militantes/{mid}/documento", response_model=MilitanteRead)
async def upload_doc(db: DbSession, ctx: CampaignCtx, _p: _CAPTURE, mid: str,
                     tipo: Annotated[str, Form()], file: Annotated[UploadFile, File()]):
    if tipo not in ("frente", "reverso", "firma"):
        raise HTTPException(status_code=422, detail="tipo inválido")
    data = await file.read()
    if len(data) > _MAX_DOC_BYTES:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande")
    m = militante_service.upload_documento(db, ctx, mid, tipo, data,
                                            file.content_type or "application/octet-stream")
    if m is None:
        raise HTTPException(status_code=404, detail="Militante no encontrado")
    m.tiene_frente = m.credencial_frente_key is not None
    m.tiene_reverso = m.credencial_reverso_key is not None
    m.tiene_firma = m.firma_key is not None
    m.activista_nombre = None
    return MilitanteRead.model_validate(m, from_attributes=True)


@router.patch("/militantes/{mid}/estado", response_model=MilitanteRead)
def set_estado(db: DbSession, ctx: CampaignCtx, _p: _REVIEW, mid: str, data: MilitanteEstadoUpdate):
    m = militante_service.set_estado(db, ctx, mid, data)
    if m is None:
        raise HTTPException(status_code=404, detail="Militante no encontrado")
    m.tiene_frente = m.credencial_frente_key is not None
    m.tiene_reverso = m.credencial_reverso_key is not None
    m.tiene_firma = m.firma_key is not None
    m.activista_nombre = None
    return MilitanteRead.model_validate(m, from_attributes=True)


@router.get("/militantes/reveal/{mid}", response_model=MilitanteReveal)
def reveal(db: DbSession, ctx: CampaignCtx, _p: _REVIEW, mid: str):
    out = militante_service.reveal_militante(db, ctx, mid)
    if out is None:
        raise HTTPException(status_code=404, detail="Militante no encontrado")
    return MilitanteReveal.model_validate(out)
