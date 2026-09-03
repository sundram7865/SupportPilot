from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.security_headers import security_headers_middleware
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.modules.agent.router import router as agent_router
from app.modules.analytics.router import router as analytics_router
from app.modules.approvals.router import router as approvals_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.external.router import router as external_router
from app.modules.health.router import router as health_router
from app.modules.integrations.router import router as integrations_router
from app.modules.internal.router import router as internal_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.organizations.router import router as organizations_router
from app.modules.public.router import router as public_router
from app.modules.realtime.router import router as realtime_router
from app.modules.replies.router import router as replies_router
from app.modules.tickets.router import router as tickets_router
from app.modules.tools.router import router as tools_router
from app.core.error_handlers import register_error_handlers
from app.modules.knowledge.evaluation.evaluation_router import evaluation_router

configure_logging()

settings = get_settings()

app = FastAPI(
    title="SupportPilot API",
    description="Agentic AI customer support platform for e-commerce brands.",
    version="0.29.1-security-config",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ⚠️ CORS MUST BE FIRST - before any other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "x-organization-id",
        "x-dev-user-id",
        "x-dev-email",
        "x-dev-name",
        "Accept",
        "Origin",
    ],
)

# Other middleware AFTER CORS
app.middleware("http")(security_headers_middleware)

register_error_handlers(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(integrations_router)
app.include_router(internal_router)
app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(tools_router)
app.include_router(approvals_router)
app.include_router(replies_router)
app.include_router(realtime_router)
app.include_router(public_router)
app.include_router(external_router)
app.include_router(audit_router)
app.include_router(analytics_router)
app.include_router(evaluation_router)


@app.get("/")
def root():
    return {
        "service": "SupportPilot API",
        "environment": settings.environment,
        "docs": "/docs" if not settings.is_production else None,
    }