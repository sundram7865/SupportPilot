from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import (
    ApprovalRequestStatus,
    ApprovalRequestType,
    CustomerReplyDraftSource,
    CustomerReplyDraftStatus,
    TicketMessageSenderType,
    TicketTimelineEventType,
    ToolRiskLevel,
)
from app.modules.agent.models import AgentRun
from app.modules.approvals.models import ApprovalRequest
from app.modules.organizations.models import Organization
from app.modules.replies.models import CustomerReplyDraft
from app.modules.tickets.models import Ticket, TicketMessage, TicketTimelineEvent


def add_reply_timeline_event(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
    actor_user_id: UUID | None,
    event_type: TicketTimelineEventType,
    title: str,
    description: str | None = None,
) -> None:
    event = TicketTimelineEvent(
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
    )
    db.add(event)


def get_ticket_or_404(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization_id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket


def get_reply_draft_or_404(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
) -> CustomerReplyDraft:
    draft = db.scalar(
        select(CustomerReplyDraft)
        .where(CustomerReplyDraft.id == draft_id)
        .where(CustomerReplyDraft.organization_id == organization_id)
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply draft not found.",
        )

    return draft


def get_agent_run_or_404(
    db: Session,
    organization_id: UUID,
    agent_run_id: UUID,
) -> AgentRun:
    agent_run = db.scalar(
        select(AgentRun)
        .where(AgentRun.id == agent_run_id)
        .where(AgentRun.organization_id == organization_id)
    )

    if not agent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )

    return agent_run


def create_reply_draft(
    db: Session,
    organization: Organization,
    ticket_id: UUID,
    body: str,
    created_by_user_id: UUID | None,
    subject: str | None = None,
    source: CustomerReplyDraftSource = CustomerReplyDraftSource.AGENT,
    agent_run_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> CustomerReplyDraft:
    get_ticket_or_404(db, organization.id, ticket_id)

    draft = CustomerReplyDraft(
        organization_id=organization.id,
        ticket_id=ticket_id,
        agent_run_id=agent_run_id,
        created_by_user_id=created_by_user_id,
        updated_by_user_id=created_by_user_id,
        source=source.value,
        status=CustomerReplyDraftStatus.DRAFT.value,
        subject=subject,
        body=body,
        metadata_json=metadata_json,
    )

    db.add(draft)

    add_reply_timeline_event(
        db=db,
        organization_id=organization.id,
        ticket_id=ticket_id,
        actor_user_id=created_by_user_id,
        event_type=TicketTimelineEventType.REPLY_DRAFT_CREATED,
        title="Reply draft created",
        description=f"Reply draft created from {source.value}.",
    )

    db.commit()
    db.refresh(draft)

    return draft


def create_reply_draft_from_agent_run(
    db: Session,
    organization: Organization,
    ticket_id: UUID,
    agent_run_id: UUID,
    created_by_user_id: UUID | None,
) -> CustomerReplyDraft:
    get_ticket_or_404(db, organization.id, ticket_id)
    agent_run = get_agent_run_or_404(db, organization.id, agent_run_id)

    if agent_run.ticket_id != ticket_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent run does not belong to this ticket.",
        )

    draft_body = agent_run.draft_response

    if not draft_body:
        final_state = agent_run.final_state or {}
        draft_body = final_state.get("draft_response")

    if not draft_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent run has no draft response.",
        )

    return create_reply_draft(
        db=db,
        organization=organization,
        ticket_id=ticket_id,
        body=draft_body,
        created_by_user_id=created_by_user_id,
        subject=f"Reply for ticket {ticket_id}",
        source=CustomerReplyDraftSource.AI,
        agent_run_id=agent_run_id,
        metadata_json={
            "agent_run_id": str(agent_run_id),
            "decision": agent_run.decision,
            "risk_level": agent_run.risk_level,
        },
    )


def update_reply_draft(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
    updated_by_user_id: UUID | None,
    subject: str | None = None,
    body: str | None = None,
    metadata_json: dict | None = None,
) -> CustomerReplyDraft:
    draft = get_reply_draft_or_404(db, organization_id, draft_id)

    if draft.status not in {
        CustomerReplyDraftStatus.DRAFT.value,
        CustomerReplyDraftStatus.REJECTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected replies can be edited.",
        )

    if subject is not None:
        draft.subject = subject

    if body is not None:
        draft.body = body

    if metadata_json is not None:
        draft.metadata_json = metadata_json

    draft.updated_by_user_id = updated_by_user_id
    draft.status = CustomerReplyDraftStatus.DRAFT.value
    draft.rejection_reason = None
    draft.rejected_by_user_id = None
    draft.rejected_at = None

    add_reply_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        actor_user_id=updated_by_user_id,
        event_type=TicketTimelineEventType.REPLY_DRAFT_UPDATED,
        title="Reply draft updated",
        description="Reply draft was edited.",
    )

    db.commit()
    db.refresh(draft)

    return draft


def submit_reply_draft_for_approval(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
    requested_by_user_id: UUID | None,
    request_reason: str | None = None,
) -> CustomerReplyDraft:
    draft = get_reply_draft_or_404(db, organization_id, draft_id)

    if draft.status != CustomerReplyDraftStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft replies can be submitted for approval.",
        )

    approval = ApprovalRequest(
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        agent_run_id=draft.agent_run_id,
        tool_execution_id=None,
        requested_by_user_id=requested_by_user_id,
        request_type=ApprovalRequestType.CUSTOMER_REPLY.value,
        status=ApprovalRequestStatus.PENDING.value,
        title="Approval required for customer reply",
        description="A customer reply draft needs approval before it is sent.",
        risk_level=ToolRiskLevel.LOW_RISK_WRITE.value,
        tool_name=None,
        input_args={
            "reply_draft_id": str(draft.id),
            "subject": draft.subject,
            "body": draft.body,
        },
        request_reason=request_reason,
        metadata_json={
            "reply_draft_id": str(draft.id),
            "source": draft.source,
        },
    )

    db.add(approval)
    db.flush()

    draft.status = CustomerReplyDraftStatus.PENDING_APPROVAL.value
    draft.approval_request_id = approval.id

    add_reply_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        actor_user_id=requested_by_user_id,
        event_type=TicketTimelineEventType.REPLY_DRAFT_SUBMITTED_FOR_APPROVAL,
        title="Reply draft submitted for approval",
        description=request_reason,
    )

    db.commit()
    db.refresh(draft)

    return draft


def approve_reply_draft(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
    approved_by_user_id: UUID | None,
    reason: str | None = None,
) -> CustomerReplyDraft:
    draft = get_reply_draft_or_404(db, organization_id, draft_id)

    if draft.status != CustomerReplyDraftStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending approval drafts can be approved.",
        )

    now = datetime.now(timezone.utc)

    draft.status = CustomerReplyDraftStatus.APPROVED.value
    draft.approved_by_user_id = approved_by_user_id
    draft.approval_reason = reason
    draft.approved_at = now

    if draft.approval_request_id:
        approval = db.scalar(
            select(ApprovalRequest)
            .where(ApprovalRequest.id == draft.approval_request_id)
            .where(ApprovalRequest.organization_id == organization_id)
        )

        if approval:
            approval.status = ApprovalRequestStatus.APPROVED.value
            approval.decided_by_user_id = approved_by_user_id
            approval.decision_reason = reason
            approval.decided_at = now
            approval.result_json = {
                "reply_draft_id": str(draft.id),
                "reply_status": CustomerReplyDraftStatus.APPROVED.value,
            }

    add_reply_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        actor_user_id=approved_by_user_id,
        event_type=TicketTimelineEventType.REPLY_DRAFT_APPROVED,
        title="Reply draft approved",
        description=reason,
    )

    db.commit()
    db.refresh(draft)

    return draft


def reject_reply_draft(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
    rejected_by_user_id: UUID | None,
    reason: str | None = None,
) -> CustomerReplyDraft:
    draft = get_reply_draft_or_404(db, organization_id, draft_id)

    if draft.status != CustomerReplyDraftStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending approval drafts can be rejected.",
        )

    now = datetime.now(timezone.utc)

    draft.status = CustomerReplyDraftStatus.REJECTED.value
    draft.rejected_by_user_id = rejected_by_user_id
    draft.rejection_reason = reason
    draft.rejected_at = now

    if draft.approval_request_id:
        approval = db.scalar(
            select(ApprovalRequest)
            .where(ApprovalRequest.id == draft.approval_request_id)
            .where(ApprovalRequest.organization_id == organization_id)
        )

        if approval:
            approval.status = ApprovalRequestStatus.REJECTED.value
            approval.decided_by_user_id = rejected_by_user_id
            approval.decision_reason = reason
            approval.decided_at = now
            approval.result_json = {
                "reply_draft_id": str(draft.id),
                "reply_status": CustomerReplyDraftStatus.REJECTED.value,
            }

    add_reply_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        actor_user_id=rejected_by_user_id,
        event_type=TicketTimelineEventType.REPLY_DRAFT_REJECTED,
        title="Reply draft rejected",
        description=reason,
    )

    db.commit()
    db.refresh(draft)

    return draft


def create_ticket_message_from_reply_draft(
    db: Session,
    organization_id: UUID,
    draft: CustomerReplyDraft,
    sent_by_user_id: UUID | None,
) -> TicketMessage:
    """
    This helper supports small field-name differences in your TicketMessage model.
    It tries body/content/message/message_text for message content.
    """

    message_kwargs = {
        "organization_id": organization_id,
        "ticket_id": draft.ticket_id,
        "sender_type": TicketMessageSenderType.AGENT.value,
    }

    if hasattr(TicketMessage, "sender_user_id"):
        message_kwargs["sender_user_id"] = sent_by_user_id

    if hasattr(TicketMessage, "is_public"):
        message_kwargs["is_public"] = True

    if hasattr(TicketMessage, "body"):
        message_kwargs["body"] = draft.body
    elif hasattr(TicketMessage, "content"):
        message_kwargs["content"] = draft.body
    elif hasattr(TicketMessage, "message"):
        message_kwargs["message"] = draft.body
    elif hasattr(TicketMessage, "message_text"):
        message_kwargs["message_text"] = draft.body
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TicketMessage model has no supported message body field.",
        )

    message = TicketMessage(**message_kwargs)
    db.add(message)
    db.flush()

    return message


def send_reply_draft(
    db: Session,
    organization_id: UUID,
    draft_id: UUID,
    sent_by_user_id: UUID | None,
    send_notes: str | None = None,
) -> CustomerReplyDraft:
    draft = get_reply_draft_or_404(db, organization_id, draft_id)

    if draft.status not in {
        CustomerReplyDraftStatus.APPROVED.value,
        CustomerReplyDraftStatus.DRAFT.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved or draft replies can be sent.",
        )

    if draft.status == CustomerReplyDraftStatus.DRAFT.value:
        # For now, manual agent drafts can be sent directly.
        # If you want strict approval for every reply, remove DRAFT from allowed statuses above.
        pass

    message = create_ticket_message_from_reply_draft(
        db=db,
        organization_id=organization_id,
        draft=draft,
        sent_by_user_id=sent_by_user_id,
    )

    now = datetime.now(timezone.utc)

    draft.status = CustomerReplyDraftStatus.SENT.value
    draft.sent_by_user_id = sent_by_user_id
    draft.sent_message_id = message.id
    draft.send_notes = send_notes
    draft.sent_at = now

    add_reply_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=draft.ticket_id,
        actor_user_id=sent_by_user_id,
        event_type=TicketTimelineEventType.CUSTOMER_REPLY_SENT,
        title="Customer reply sent",
        description="Approved reply was sent to the customer.",
    )

    db.commit()
    db.refresh(draft)

    return draft