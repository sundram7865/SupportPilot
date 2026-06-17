from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import configure_logging
from app.modules.agent.router import router as agent_router
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.integrations.router import router as integrations_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.organizations.router import router as organizations_router
from app.modules.tickets.router import router as tickets_router
from app.modules.tools.router import router as tools_router

configure_logging()

app = FastAPI(
    title="SupportPilot API",
    description="Agentic AI customer support platform for e-commerce brands.",
    version="0.8.0-phase-8",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(integrations_router)
app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(tools_router)


@app.get("/")
def root():
    return {
        "service": "SupportPilot API",
        "phase": "8",
        "docs": "/docs",
    }