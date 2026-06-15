"""ORM models.

Importing the models here ensures they are registered on ``Base.metadata``
for Alembic autogeneration and ``create_all``.
"""

from app.models.audit_log import AuditLog
from app.models.electoral_area import ElectoralArea
from app.models.organization import Organization
from app.models.user import User

__all__ = ["AuditLog", "ElectoralArea", "Organization", "User"]
