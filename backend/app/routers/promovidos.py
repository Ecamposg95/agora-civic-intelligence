"""GET /promovidos — role+territory scoped promovidos table with electoral context."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import CampaignCtx, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.promovido import PromovidoList, PromovidoRead
from app.services import promovido_service

router = APIRouter(tags=["promovidos"])

_READ = Annotated[object, Depends(require_roles(
    UserRole.ADMIN, UserRole.COORDINADOR, UserRole.LIDER))]


@router.get("/promovidos", response_model=PromovidoList)
def list_promovidos(
    db: DbSession, ctx: CampaignCtx, _perm: _READ,
    seccion: Annotated[Optional[str], Query()] = None,
    promotor: Annotated[Optional[str], Query()] = None,
    prioridad: Annotated[Optional[str], Query()] = None,
    q: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PromovidoList:
    rows, total, has_territory = promovido_service.list_promovidos(
        db, ctx, seccion=seccion, promotor=promotor, prioridad=prioridad,
        q=q, limit=limit, offset=offset)
    return PromovidoList(
        items=[PromovidoRead.model_validate(r, from_attributes=True) for r in rows],
        total=total, limit=limit, offset=offset, has_territory=has_territory)
