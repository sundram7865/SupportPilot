from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ExternalTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3, max_length=5000)

    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr
    customer_phone: str | None = Field(default=None, max_length=50)

    external_order_id: str | None = Field(default=None, max_length=100)

    priority: str = Field(default="MEDIUM", max_length=50)
    category: str = Field(default="OTHER", max_length=80)
    source: str = Field(default="API", max_length=50)

    metadata_json: dict | None = None


class ExternalTicketCreateResponse(BaseModel):
    id: str
    organization_id: str
    ticket_number: str
    subject: str
    status: str
    priority: str
    category: str
    source: str
    customer_email: str
    external_order_id: str | None = None
    created_at: datetime | None = None
    message: str