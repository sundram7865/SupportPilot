import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

API_KEY = os.getenv("URBANKART_API_KEY", "dev_urbankart_key")

app = FastAPI(
    title="UrbanKart Mock Support API",
    description="Mock e-commerce support APIs consumed by SupportPilot.",
    version="0.1.0-phase-1",
)


def verify_api_key(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid UrbanKart API key")


ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_email": "rahul@example.com",
        "status": "OUT_FOR_DELIVERY",
        "total_amount": 1499,
        "currency": "INR",
        "items": [
            {
                "name": "UrbanStep Sneakers",
                "sku": "SHOE-001",
                "quantity": 1,
                "price": 1499,
            }
        ],
        "created_at": "2026-06-10T10:30:00Z",
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_email": "ananya@example.com",
        "status": "FAILED",
        "total_amount": 1499,
        "currency": "INR",
        "items": [
            {
                "name": "TravelPro Backpack",
                "sku": "BAG-001",
                "quantity": 1,
                "price": 1499,
            }
        ],
        "created_at": "2026-06-11T09:20:00Z",
    },
}

PAYMENTS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "payment_status": "SUCCESS",
        "amount": 1499,
        "currency": "INR",
        "payment_method": "UPI",
        "payment_reference": "pay_ord1001",
        "paid_at": "2026-06-10T10:31:00Z",
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "payment_status": "SUCCESS",
        "amount": 1499,
        "currency": "INR",
        "payment_method": "UPI",
        "payment_reference": "pay_ord1002",
        "paid_at": "2026-06-11T09:21:00Z",
    },
}

SHIPMENTS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "shipment_status": "OUT_FOR_DELIVERY",
        "courier": "Delhivery",
        "tracking_id": "TRK-77821",
        "estimated_delivery": (
            datetime.now(timezone.utc) + timedelta(hours=8)
        ).isoformat(),
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "shipment_status": "NOT_SHIPPED",
        "courier": None,
        "tracking_id": None,
        "estimated_delivery": None,
    },
}

CUSTOMERS = {
    "rahul@example.com": {
        "customer_id": "CUST-1001",
        "name": "Rahul Jain",
        "email": "rahul@example.com",
        "phone_masked": "9334******",
        "total_orders": 8,
        "lifetime_value": 12450,
        "customer_type": "VIP",
    },
    "ananya@example.com": {
        "customer_id": "CUST-1002",
        "name": "Ananya Gupta",
        "email": "ananya@example.com",
        "phone_masked": "9876******",
        "total_orders": 2,
        "lifetime_value": 2998,
        "customer_type": "REGULAR",
    },
}


class RefundRequest(BaseModel):
    order_id: str
    amount: float
    reason: str
    requested_by: str
    support_ticket_id: str
    idempotency_key: str


class ReplacementRequest(BaseModel):
    order_id: str
    reason: str
    support_ticket_id: str
    evidence_urls: list[str] = []
    idempotency_key: str


@app.get("/api/support/health")
def health(x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)

    return {
        "status": "ok",
        "service": "urbankart-mock-support-api",
    }


@app.get("/api/support/orders/{order_id}")
def get_order(order_id: str, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)

    order = ORDERS.get(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@app.get("/api/support/orders/{order_id}/payment")
def get_payment(order_id: str, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)

    payment = PAYMENTS.get(order_id)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@app.get("/api/support/orders/{order_id}/shipment")
def get_shipment(order_id: str, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)

    shipment = SHIPMENTS.get(order_id)

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment


@app.get("/api/support/customers/by-email")
def get_customer_by_email(email: str, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)

    customer = CUSTOMERS.get(email)

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@app.post("/api/support/refunds/request")
def request_refund(
    payload: RefundRequest,
    x_api_key: str | None = Header(default=None),
):
    verify_api_key(x_api_key)

    return {
        "refund_request_id": f"REF-{payload.order_id}",
        "status": "REQUESTED",
        "requires_internal_processing": True,
        "message": "Refund request created successfully",
        "idempotency_key": payload.idempotency_key,
    }


@app.post("/api/support/replacements/request")
def request_replacement(
    payload: ReplacementRequest,
    x_api_key: str | None = Header(default=None),
):
    verify_api_key(x_api_key)

    return {
        "replacement_request_id": f"REP-{payload.order_id}",
        "status": "REQUESTED",
        "message": "Replacement request created successfully",
        "idempotency_key": payload.idempotency_key,
    }