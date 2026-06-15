from dataclasses import dataclass

from app.common.enums import TicketStatus


ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.WAITING_FOR_INTERNAL_REVIEW,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.WAITING_FOR_INTERNAL_REVIEW,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.WAITING_FOR_CUSTOMER: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.WAITING_FOR_INTERNAL_REVIEW: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    },
    TicketStatus.RESOLVED: {
        TicketStatus.CLOSED,
        TicketStatus.IN_PROGRESS,
    },
    TicketStatus.CLOSED: set(),
}


TERMINAL_STATUSES: set[TicketStatus] = {
    TicketStatus.CLOSED,
}


REOPEN_ALLOWED_FROM: set[TicketStatus] = {
    TicketStatus.RESOLVED,
}


@dataclass(frozen=True)
class TransitionValidationResult:
    allowed: bool
    reason: str | None = None


def validate_status_transition(
    from_status: str,
    to_status: str,
) -> TransitionValidationResult:
    try:
        parsed_from_status = TicketStatus(from_status)
        parsed_to_status = TicketStatus(to_status)
    except ValueError:
        return TransitionValidationResult(
            allowed=False,
            reason="Unknown ticket status.",
        )

    if parsed_from_status == parsed_to_status:
        return TransitionValidationResult(
            allowed=False,
            reason=f"Ticket is already in {parsed_to_status.value}.",
        )

    allowed_targets = ALLOWED_STATUS_TRANSITIONS.get(parsed_from_status, set())

    if parsed_to_status not in allowed_targets:
        return TransitionValidationResult(
            allowed=False,
            reason=f"Invalid transition from {parsed_from_status.value} to {parsed_to_status.value}.",
        )

    return TransitionValidationResult(allowed=True)


def get_lifecycle_rules() -> dict[str, list[str]]:
    return {
        status.value: sorted([target.value for target in targets])
        for status, targets in ALLOWED_STATUS_TRANSITIONS.items()
    }


def is_terminal_status(status: str) -> bool:
    try:
        return TicketStatus(status) in TERMINAL_STATUSES
    except ValueError:
        return False