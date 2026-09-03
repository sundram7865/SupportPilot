import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.worker.tasks.sla import run_sla_check

router = APIRouter(prefix="/internal/jobs", tags=["Internal Jobs"])


@router.post("/check-sla")
def run_sla_job(
    x_internal_job_secret: str | None = Header(default=None),
):
    settings = get_settings()

    if not x_internal_job_secret or not secrets.compare_digest(
        x_internal_job_secret,
        settings.internal_job_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal job secret.",
        )

    db = SessionLocal()
    try:
        return run_sla_check(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()