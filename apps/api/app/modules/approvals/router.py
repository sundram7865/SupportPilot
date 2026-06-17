from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.approvals.models import ApprovalRequest
from app.modules.approvals.schemas import (
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
    CreateApprovalRequestBody,
    DecideApprovalRequestBody,
)
from app.modules.approvals.service import (
    approve_request,
    create_approval_request_for_tool_execution,
    get_approval_or_404,
    reject_request,
)
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.users.models import User

router = APIRouter(prefix="/approvals", tags=["Approvals"])


def to_approval_response(approval: ApprovalRequest) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=str(approval.id),
        organization_id=str(approval.organization_id),
        ticket_id=str(approval.ticket_id) if approval.ticket_id else None,
        agent_run_id=str(approval.agent_run_id) if approval.agent_run_id else None,
        tool_execution_id=(
            str(approval.tool_execution_id) if approval.tool_execution_id else None
        ),
        requested_by_user_id=(
            str(approval.requested_by_user_id)
            if approval.requested_by_user_id
            else None
        ),
        decided_by_user_id=(
            str(approval.decided_by_user_id) if approval.decided_by_user_id else None
        ),
        request_type=approval.request_type,
        status=approval.status,
        title=approval.title,
        description=approval.description,
        risk_level=approval.risk_level,
        tool_name=approval.tool_name,
        input_args=approval.input_args,
        request_reason=approval.request_reason,
        decision_reason=approval.decision_reason,
        result_json=approval.result_json,
        metadata_json=approval.metadata_json,
        created_at=approval.created_at,
        decided_at=approval.decided_at,
    )


@router.post(
    "/tool-executions/{execution_id}/request",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_REQUEST))],
)
def request_tool_execution_approval(
    execution_id: UUID,
    payload: CreateApprovalRequestBody,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    approval = create_approval_request_for_tool_execution(
        db=db,
        organization_id=organization.id,
        execution_id=execution_id,
        requested_by_user_id=current_user.id,
        request_reason=payload.request_reason,
        metadata_json=payload.metadata_json,
    )

    return to_approval_response(approval)


@router.get(
    "",
    response_model=ApprovalRequestListResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_READ))],
)
def list_approvals(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(ApprovalRequest).where(
        ApprovalRequest.organization_id == organization.id
    )

    count_query = select(func.count(ApprovalRequest.id)).where(
        ApprovalRequest.organization_id == organization.id
    )

    if status_filter:
        query = query.where(ApprovalRequest.status == status_filter)
        count_query = count_query.where(ApprovalRequest.status == status_filter)

    total = db.scalar(count_query) or 0

    approvals = db.scalars(
        query.order_by(desc(ApprovalRequest.created_at))
        .limit(limit)
        .offset(offset)
    ).all()

    return ApprovalRequestListResponse(
        items=[to_approval_response(approval) for approval in approvals],
        total=total,
    )


@router.get(
    "/{approval_id}",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_READ))],
)
def get_approval(
    approval_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    approval = get_approval_or_404(
        db=db,
        organization_id=organization.id,
        approval_id=approval_id,
    )

    return to_approval_response(approval)


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_DECIDE))],
)
async def approve_approval(
    approval_id: UUID,
    payload: DecideApprovalRequestBody,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    approval = await approve_request(
        db=db,
        organization=organization,
        approval_id=approval_id,
        decided_by_user_id=current_user.id,
        decision_reason=payload.decision_reason,
    )

    return to_approval_response(approval)


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_DECIDE))],
)
def reject_approval(
    approval_id: UUID,
    payload: DecideApprovalRequestBody,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    approval = reject_request(
        db=db,
        organization_id=organization.id,
        approval_id=approval_id,
        decided_by_user_id=current_user.id,
        decision_reason=payload.decision_reason,
    )

    return to_approval_response(approval)


@router.get(
    "/tickets/{ticket_id}",
    response_model=ApprovalRequestListResponse,
    dependencies=[Depends(require_permission(Permission.APPROVAL_READ))],
)
def list_ticket_approvals(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    total = (
        db.scalar(
            select(func.count(ApprovalRequest.id))
            .where(ApprovalRequest.organization_id == organization.id)
            .where(ApprovalRequest.ticket_id == ticket_id)
        )
        or 0
    )

    approvals = db.scalars(
        select(ApprovalRequest)
        .where(ApprovalRequest.organization_id == organization.id)
        .where(ApprovalRequest.ticket_id == ticket_id)
        .order_by(desc(ApprovalRequest.created_at))
    ).all()

    return ApprovalRequestListResponse(
        items=[to_approval_response(approval) for approval in approvals],
        total=total,
    )