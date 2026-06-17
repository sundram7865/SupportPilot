import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import (
    ApprovalRequestStatus,
    ApprovalRequestType,
    ToolRiskLevel,
)
from app.db.base import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "tool_execution_id",
            name="uq_approval_requests_org_tool_execution",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tool_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    request_type: Mapped[str] = mapped_column(
        String(80),
        default=ApprovalRequestType.TOOL_EXECUTION.value,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default=ApprovalRequestStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_level: Mapped[str] = mapped_column(
        String(50),
        default=ToolRiskLevel.HIGH_RISK_WRITE.value,
        nullable=False,
        index=True,
    )

    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    input_args: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )