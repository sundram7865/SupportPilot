from enum import StrEnum

from app.common.enums import OrganizationRole


class Permission(StrEnum):
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_UPDATE = "organization:update"

    TEAM_READ = "team:read"
    TEAM_INVITE = "team:invite"
    TEAM_UPDATE = "team:update"
    TEAM_REMOVE = "team:remove"

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
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.ADMIN: {
        Permission.ORGANIZATION_READ,
        Permission.ORGANIZATION_UPDATE,
        Permission.TEAM_READ,
        Permission.TEAM_INVITE,
        Permission.TEAM_UPDATE,
        Permission.AUDIT_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.MANAGER: {
        Permission.ORGANIZATION_READ,
        Permission.TEAM_READ,
        Permission.ANALYTICS_VIEW,
    },
    OrganizationRole.SUPPORT_AGENT: {
        Permission.ORGANIZATION_READ,
    },
    OrganizationRole.VIEWER: {
        Permission.ORGANIZATION_READ,
    },
}


def role_has_permission(role: str, permission: Permission) -> bool:
    try:
        parsed_role = OrganizationRole(role)
    except ValueError:
        return False

    return permission in ROLE_PERMISSIONS.get(parsed_role, set())