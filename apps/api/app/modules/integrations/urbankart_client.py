import time
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.common.enums import ExternalApiStatus, IntegrationProvider
from app.modules.integrations.models import ExternalApiLog, IntegrationConnection


class UrbanKartClient:
    def __init__(
        self,
        connection: IntegrationConnection,
        api_key: str,
        db: Session,
    ):
        self.connection = connection
        self.organization_id = connection.organization_id
        self.integration_connection_id = connection.id
        self.base_url = connection.base_url.rstrip("/")
        self.api_key = api_key
        self.db = db
        self.timeout_seconds = 5.0

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def _write_log(
        self,
        method: str,
        endpoint: str,
        status: ExternalApiStatus,
        status_code: int | None,
        duration_ms: int,
        request_payload: dict | None = None,
        response_payload: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        log = ExternalApiLog(
            organization_id=self.organization_id,
            integration_connection_id=self.integration_connection_id,
            provider=IntegrationProvider.URBANKART.value,
            method=method,
            endpoint=endpoint,
            status=status.value,
            status_code=status_code,
            duration_ms=duration_ms,
            request_payload=request_payload,
            response_payload=response_payload,
            error_message=error_message,
        )

        self.db.add(log)
        self.db.commit()

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        started_at = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=payload if method.upper() != "GET" else None,
                )

            duration_ms = int((time.perf_counter() - started_at) * 1000)

            try:
                response_payload = response.json()
            except Exception:
                response_payload = {"raw": response.text}

            if response.is_error:
                self._write_log(
                    method=method,
                    endpoint=endpoint,
                    status=ExternalApiStatus.FAILED,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_payload=payload,
                    response_payload=response_payload,
                    error_message=f"UrbanKart returned HTTP {response.status_code}",
                )
                response.raise_for_status()

            self._write_log(
                method=method,
                endpoint=endpoint,
                status=ExternalApiStatus.SUCCESS,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_payload=payload,
                response_payload=response_payload,
            )

            return response_payload

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started_at) * 1000)

            self._write_log(
                method=method,
                endpoint=endpoint,
                status=ExternalApiStatus.FAILED,
                status_code=None,
                duration_ms=duration_ms,
                request_payload=payload,
                error_message=str(exc),
            )

            raise

    async def health(self) -> dict:
        return await self._request("GET", "/api/support/health")

    async def get_order_details(self, order_id: str) -> dict:
        return await self._request("GET", f"/api/support/orders/{order_id}")

    async def get_payment_status(self, order_id: str) -> dict:
        return await self._request("GET", f"/api/support/orders/{order_id}/payment")

    async def get_shipment_status(self, order_id: str) -> dict:
        return await self._request("GET", f"/api/support/orders/{order_id}/shipment")

    async def request_refund(
        self,
        order_id: str,
        amount: float,
        reason: str,
        support_ticket_id: str,
        idempotency_key: str,
    ) -> dict:
        return await self._request(
            "POST",
            "/api/support/refunds/request",
            {
                "order_id": order_id,
                "amount": amount,
                "reason": reason,
                "requested_by": "supportpilot",
                "support_ticket_id": support_ticket_id,
                "idempotency_key": idempotency_key,
            },
        )