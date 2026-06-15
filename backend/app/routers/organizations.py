"""Organizations router — tenant-scoped, paginated.

Non-superadmins only ever see their own organization.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.dependencies import DbSession, Tenant
from app.models.organization import Organization
from app.schemas.organization import OrganizationRead
from app.schemas.pagination import Page
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=Page[OrganizationRead], summary="List organizations")
def list_organizations(
    db: DbSession,
    ctx: Tenant,
    pagination: PaginationParams = Depends(),
) -> Page[OrganizationRead]:
    """List organizations visible to the caller."""
    filters = [Organization.deleted_at.is_(None)]
    if not ctx.is_superadmin:
        filters.append(Organization.id == ctx.organization_id)

    total = db.scalar(select(func.count(Organization.id)).where(*filters)) or 0
    rows = (
        db.execute(
            select(Organization)
            .where(*filters)
            .order_by(Organization.created_at)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        .scalars()
        .all()
    )

    return Page[OrganizationRead](
        items=[OrganizationRead.model_validate(r) for r in rows],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
