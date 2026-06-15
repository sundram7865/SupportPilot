from enum import StrEnum


class OrganizationRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    VIEWER = "VIEWER"

class IntegrationProvider(StrEnum):
    URBANKART = "URBANKART"


class IntegrationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class ExternalApiStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    
class MemberStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    SUSPENDED = "SUSPENDED"