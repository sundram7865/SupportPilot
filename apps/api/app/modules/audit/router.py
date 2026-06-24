from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.modules.auth.dependencies import get_current_organization, require_permission
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


def to_audit_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse.model_validate(log)


@router.get(
    "",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_permission(Permission.AUDIT_VIEW))],
)
def list_audit_logs(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: UUID | None = Query(default=None),
    ticket_id: UUID | None = Query(default=None),
    actor_user_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    filters = [AuditLog.organization_id == organization.id]

    if action:
        filters.append(AuditLog.action == action)

    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    if resource_id:
        filters.append(AuditLog.resource_id == resource_id)

    if ticket_id:
        filters.append(AuditLog.ticket_id == ticket_id)

    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)

    total = db.scalar(select(func.count(AuditLog.id)).where(and_(*filters))) or 0

    logs = db.scalars(
        select(AuditLog)
        .where(and_(*filters))
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
        .offset(offset)
    ).all()

    return AuditLogListResponse(
        items=[to_audit_response(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )