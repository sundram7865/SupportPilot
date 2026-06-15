import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    TicketCategory,
    TicketMessageSenderType,
    TicketPriority,
    TicketSource,
    TicketStatus,
    TicketTimelineEventType,
)
from app.db.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

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

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50),
        default=TicketStatus.OPEN.value,
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        default=TicketPriority.MEDIUM.value,
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(80),
        default=TicketCategory.OTHER.value,
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default=TicketSource.SUPPORT_FORM.value,
        nullable=False,
    )

    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    customer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    external_order_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    ai_confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
    )

    internal_notes = relationship(
        "TicketInternalNote",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketInternalNote.created_at",
    )

    timeline_events = relationship(
        "TicketTimelineEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketTimelineEvent.created_at",
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

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

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_type: Mapped[str] = mapped_column(
        String(50),
        default=TicketMessageSenderType.CUSTOMER.value,
        nullable=False,
        index=True,
    )

    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    ticket = relationship("Ticket", back_populates="messages")


class TicketInternalNote(Base):
    __tablename__ = "ticket_internal_notes"

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

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    ticket = relationship("Ticket", back_populates="internal_notes")


class TicketTimelineEvent(Base):
    __tablename__ = "ticket_timeline_events"

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

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(80),
        default=TicketTimelineEventType.TICKET_CREATED.value,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    ticket = relationship("Ticket", back_populates="timeline_events")