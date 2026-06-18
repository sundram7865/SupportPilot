from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.replies.models import CustomerReplyDraft
from app.modules.replies.schemas import (
    CreateReplyDraftRequest,
    DecideReplyDraftRequest,
    ReplyDraftListResponse,
    ReplyDraftResponse,
    SendReplyDraftRequest,
    SubmitReplyDraftApprovalRequest,
    UpdateReplyDraftRequest,
)
from app.modules.replies.service import (
    approve_reply_draft,
    create_reply_draft,
    create_reply_draft_from_agent_run,
    get_reply_draft_or_404,
    reject_reply_draft,
    send_reply_draft,
    submit_reply_draft_for_approval,
    update_reply_draft,
)
from app.modules.users.models import User

router = APIRouter(prefix="/replies", tags=["Customer Replies"])


def to_reply_draft_response(draft: CustomerReplyDraft) -> ReplyDraftResponse:
    return ReplyDraftResponse(
        id=str(draft.id),
        organization_id=str(draft.organization_id),
        ticket_id=str(draft.ticket_id),
        agent_run_id=str(draft.agent_run_id) if draft.agent_run_id else None,
        approval_request_id=(
            str(draft.approval_request_id) if draft.approval_request_id else None
        ),
        created_by_user_id=(
            str(draft.created_by_user_id) if draft.created_by_user_id else None
        ),
        updated_by_user_id=(
            str(draft.updated_by_user_id) if draft.updated_by_user_id else None
        ),
        approved_by_user_id=(
            str(draft.approved_by_user_id) if draft.approved_by_user_id else None
        ),
        rejected_by_user_id=(
            str(draft.rejected_by_user_id) if draft.rejected_by_user_id else None
        ),
        sent_by_user_id=str(draft.sent_by_user_id) if draft.sent_by_user_id else None,
        sent_message_id=str(draft.sent_message_id) if draft.sent_message_id else None,
        source=draft.source,
        status=draft.status,
        subject=draft.subject,
        body=draft.body,
        rejection_reason=draft.rejection_reason,
        approval_reason=draft.approval_reason,
        send_notes=draft.send_notes,
        metadata_json=draft.metadata_json,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        approved_at=draft.approved_at,
        rejected_at=draft.rejected_at,
        sent_at=draft.sent_at,
    )


@router.post(
    "/drafts",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_DRAFT))],
)
def create_draft(
    payload: CreateReplyDraftRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = create_reply_draft(
        db=db,
        organization=organization,
        ticket_id=payload.ticket_id,
        body=payload.body,
        created_by_user_id=current_user.id,
        subject=payload.subject,
        source=payload.source,
        metadata_json=payload.metadata_json,
    )

    return to_reply_draft_response(draft)


@router.post(
    "/tickets/{ticket_id}/draft-from-agent-run/{agent_run_id}",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_DRAFT))],
)
def create_draft_from_agent(
    ticket_id: UUID,
    agent_run_id: UUID,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = create_reply_draft_from_agent_run(
        db=db,
        organization=organization,
        ticket_id=ticket_id,
        agent_run_id=agent_run_id,
        created_by_user_id=current_user.id,
    )

    return to_reply_draft_response(draft)


@router.get(
    "/tickets/{ticket_id}/drafts",
    response_model=ReplyDraftListResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_READ))],
)
def list_ticket_drafts(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    total = (
        db.scalar(
            select(func.count(CustomerReplyDraft.id))
            .where(CustomerReplyDraft.organization_id == organization.id)
            .where(CustomerReplyDraft.ticket_id == ticket_id)
        )
        or 0
    )

    drafts = db.scalars(
        select(CustomerReplyDraft)
        .where(CustomerReplyDraft.organization_id == organization.id)
        .where(CustomerReplyDraft.ticket_id == ticket_id)
        .order_by(desc(CustomerReplyDraft.created_at))
    ).all()

    return ReplyDraftListResponse(
        items=[to_reply_draft_response(draft) for draft in drafts],
        total=total,
    )


@router.get(
    "/drafts/{draft_id}",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_READ))],
)
def get_draft(
    draft_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    draft = get_reply_draft_or_404(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
    )

    return to_reply_draft_response(draft)


@router.patch(
    "/drafts/{draft_id}",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_DRAFT))],
)
def update_draft(
    draft_id: UUID,
    payload: UpdateReplyDraftRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = update_reply_draft(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
        updated_by_user_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        metadata_json=payload.metadata_json,
    )

    return to_reply_draft_response(draft)


@router.post(
    "/drafts/{draft_id}/submit-approval",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_REQUEST))],
)
def submit_draft_for_approval(
    draft_id: UUID,
    payload: SubmitReplyDraftApprovalRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = submit_reply_draft_for_approval(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
        requested_by_user_id=current_user.id,
        request_reason=payload.request_reason,
    )

    return to_reply_draft_response(draft)


@router.post(
    "/drafts/{draft_id}/approve",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_APPROVE))],
)
def approve_draft(
    draft_id: UUID,
    payload: DecideReplyDraftRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = approve_reply_draft(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
        approved_by_user_id=current_user.id,
        reason=payload.reason,
    )

    return to_reply_draft_response(draft)


@router.post(
    "/drafts/{draft_id}/reject",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_APPROVE))],
)
def reject_draft(
    draft_id: UUID,
    payload: DecideReplyDraftRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = reject_reply_draft(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
        rejected_by_user_id=current_user.id,
        reason=payload.reason,
    )

    return to_reply_draft_response(draft)


@router.post(
    "/drafts/{draft_id}/send",
    response_model=ReplyDraftResponse,
    dependencies=[Depends(require_permission(Permission.REPLY_SEND))],
)
def send_draft(
    draft_id: UUID,
    payload: SendReplyDraftRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    draft = send_reply_draft(
        db=db,
        organization_id=organization.id,
        draft_id=draft_id,
        sent_by_user_id=current_user.id,
        send_notes=payload.send_notes,
    )

    return to_reply_draft_response(draft)