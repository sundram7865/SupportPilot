"""RAG Evaluation API Routes"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_organization, require_permission
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.knowledge.evaluation.evaluate_rag import (
    run_golden_evaluation,
    quick_retrieval_test,
    GOLDEN_QUESTIONS,
)

evaluation_router = APIRouter(prefix="/knowledge/evaluation", tags=["RAG Evaluation"])


@evaluation_router.post(
    "/golden",
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
async def evaluate_with_golden_questions(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Evaluate RAG pipeline using pre-defined golden questions."""
    results = await run_golden_evaluation(db, organization.id)
    return results


@evaluation_router.get("/questions")
async def get_golden_questions():
    """View the pre-defined golden questions"""
    return {
        "count": len(GOLDEN_QUESTIONS),
        "questions": GOLDEN_QUESTIONS,
    }


@evaluation_router.post(
    "/search-test",
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
async def test_search_with_ai(
    query: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Test a single query: retrieve + generate answer"""
    results = await quick_retrieval_test(db, organization.id, query)
    return results