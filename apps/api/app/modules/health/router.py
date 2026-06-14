from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router =APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    return{
        "status":"ok",
        "service": "supportpilot-api",
        "version": "phase-1",
    }
    
@router.get("/ready")
def readiness_check():
    settings=get_settings()
    
    database_status="unknown"
    redis_status = "unknown"
    
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as exc:
        database_status = f"error: {str(exc)}"

    try:
        redis = Redis.from_url(settings.redis_url)
        redis.ping()
        redis_status = "ok"
    except Exception as exc:
        redis_status = f"error: {str(exc)}"

    is_ready = database_status == "ok" and redis_status == "ok"

    return {
        "ready": is_ready,
        "checks": {
            "database": database_status,
            "redis": redis_status,
        },
    }