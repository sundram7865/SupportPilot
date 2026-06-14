from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.modules.integrations.urbankart_client import UrbanKartClient

router = APIRouter(prefix="/integrations/urbankart", tags=["UrbanKart Integration"])

def get_urbankart_client() -> UrbanKartClient:
    settings = get_settings()
    return UrbanKartClient(
        base_url=settings.urbankart_base_url,
        api_key=settings.urbankart_api_key,
    )
    
@router.post("/test-connection")
async def test_urbankart_connection():
    client = get_urbankart_client()

    try:
        result = await client.health()
        return {
            "status": "connected",
            "provider": "urbankart",
            "result": result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"UrbanKart connection failed: {str(exc)}",
        )
        
@router.get("/orders/{order_id}")
async def get_order_details(order_id: str):
    client = get_urbankart_client()

    try:
        order = await client.get_order_details(order_id)
        payment = await client.get_payment_status(order_id)
        shipment = await client.get_shipment_status(order_id)

        return {
            "order": order,
            "payment": payment,
            "shipment": shipment,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch UrbanKart order data: {str(exc)}",
        )