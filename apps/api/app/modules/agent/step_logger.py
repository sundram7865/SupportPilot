import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.enums import AgentStepStatus
from app.modules.agent.models import AgentRunStep


def run_logged_step(
    db: Session,
    organization_id: UUID,
    agent_run_id: UUID,
    ticket_id: UUID,
    step_name: str,
    input_json: dict | None,
    fn,
) -> Any:
    started_at = time.perf_counter()

    step = AgentRunStep(
        organization_id=organization_id,
        agent_run_id=agent_run_id,
        ticket_id=ticket_id,
        step_name=step_name,
        status=AgentStepStatus.STARTED.value,
        input_json=input_json,
    )

    db.add(step)
    db.commit()
    db.refresh(step)

    try:
        output = fn()

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        step.status = AgentStepStatus.COMPLETED.value
        step.output_json = output if isinstance(output, dict) else {"output": output}
        step.duration_ms = duration_ms
        step.completed_at = datetime.now(timezone.utc)

        db.commit()

        return output

    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        step.status = AgentStepStatus.FAILED.value
        step.error_message = str(exc)
        step.duration_ms = duration_ms
        step.completed_at = datetime.now(timezone.utc)

        db.commit()

        raise