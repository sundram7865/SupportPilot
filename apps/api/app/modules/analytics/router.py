from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytics.schemas import AnalyticsOverviewResponse
from app.modules.analytics.service import get_analytics_overview
from app.modules.auth.dependencies import get_current_organization, require_permission
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    dependencies=[Depends(require_permission(Permission.ANALYTICS_VIEW))],
)
def get_overview(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    return get_analytics_overview(
        db=db,
        organization_id=organization.id,
    )