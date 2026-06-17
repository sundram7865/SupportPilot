from enum import StrEnum

from app.common.enums import OrganizationRole


class Permission(StrEnum):
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_UPDATE = "organization:update"

    TEAM_READ = "team:read"
    TEAM_INVITE = "team:invite"
    TEAM_UPDATE = "team:update"
    TEAM_REMOVE = "team:remove"

    TICKET_READ = "ticket:read"
    TICKET_CREATE = "ticket:create"
    TICKET_UPDATE = "ticket:update"
    TICKET_ASSIGN = "ticket:assign"
    TICKET_INTERNAL_NOTE = "ticket:internal_note"

    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_CREATE = "knowledge:create"
    KNOWLEDGE_UPDATE = "knowledge:update"
    KNOWLEDGE_DELETE = "knowledge:delete"
    KNOWLEDGE_INGEST = "knowledge:ingest"

    AGENT_RUN = "agent:run"
    AGENT_READ = "agent:read"

    AUDIT_VIEW = "audit:view"
    ANALYTICS_VIEW = "analytics:view"


ROLE_PERMISSIONS: dict[OrganizationRole, set[Permission]] = {
    OrganizationRole.OWNER: {
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_UPDATE,
        Permission.TEAM_READ,
        Permission.TEAM_INVITE,
        Permission.TEAM_UPDATE,
        Permission.TEAM_REMOVE,
        Permission.TICKET_READ,
        Permission.TICKET_CREATE,
        Permission.TICKET_UPDATE,
        Permission.TICKET_ASSIGN,
        Permission.TICKET_INTERNAL_NOTE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_CREATE,
        Permission.KNOWLEDGE_UPDATE,
        Permission.KNOWLEDGE_DELETE,
        Permission.KNOWLEDGE_INGEST,
        Permission.AGENT_RUN,
        Permission.AGENT_READ,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.ADMIN: {
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_UPDATE,
        Permission.TEAM_READ,
        Permission.TEAM_INVITE,
        Permission.TEAM_UPDATE,
        Permission.TICKET_READ,
        Permission.TICKET_CREATE,
        Permission.TICKET_UPDATE,
        Permission.TICKET_ASSIGN,
        Permission.TICKET_INTERNAL_NOTE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_CREATE,
        Permission.KNOWLEDGE_UPDATE,
        Permission.KNOWLEDGE_DELETE,
        Permission.KNOWLEDGE_INGEST,
        Permission.AGENT_RUN,
        Permission.AGENT_READ,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.MANAGER: {
        Permission.ORGANIZATION_READ,
        Permission.TEAM_READ,
        Permission.TICKET_READ,
        Permission.TICKET_CREATE,
        Permission.TICKET_UPDATE,
        Permission.TICKET_ASSIGN,
        Permission.TICKET_INTERNAL_NOTE,
        Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_CREATE,
        Permission.KNOWLEDGE_UPDATE,
        Permission.KNOWLEDGE_INGEST,
        Permission.AGENT_RUN,
        Permission.AGENT_READ,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.SUPPORT_AGENT: {
        Permission.ORGANIZATION_READ,
        Permission.TICKET_READ,
        Permission.TICKET_CREATE,
        Permission.TICKET_UPDATE,
        Permission.TICKET_INTERNAL_NOTE,
        Permission.KNOWLEDGE_READ,
        Permission.AGENT_RUN,
        Permission.AGENT_READ,
    },
    OrganizationRole.VIEWER: {
        Permission.ORGANIZATION_READ,
        Permission.TICKET_READ,
        Permission.KNOWLEDGE_READ,
        Permission.AGENT_READ,
    },
}


def role_has_permission(role: str, permission: Permission) -> bool:
    try:
        parsed_role = OrganizationRole(role)
    except ValueError:
        return False

    return permission in ROLE_PERMISSIONS.get(parsed_role, set())