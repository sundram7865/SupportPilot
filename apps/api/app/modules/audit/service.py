from uuid import UUID

from sqlalchemy.orm import Session

from app.common.enums import AuditAction, AuditResourceType
from app.modules.audit.models import AuditLog


def enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def create_audit_log(
    db: Session,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: AuditAction | str,
    resource_type: AuditResourceType | str,
    resource_id: UUID | None = None,
    ticket_id: UUID | None = None,
    agent_run_id: UUID | None = None,
    tool_execution_id: UUID | None = None,
    approval_request_id: UUID | None = None,
    reply_draft_id: UUID | None = None,
    description: str | None = None,
    metadata_json: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=enum_value(action),
        resource_type=enum_value(resource_type),
        resource_id=resource_id,
        ticket_id=ticket_id,
        agent_run_id=agent_run_id,
        tool_execution_id=tool_execution_id,
        approval_request_id=approval_request_id,
        reply_draft_id=reply_draft_id,
        description=description,
        metadata_json=metadata_json,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_log)
    db.flush()

    return audit_log