import httpx

class UrbanKartClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "accept": "application/json",
        }
    async def health(self) -> dict:
        url = f"{self.base_url}/api/support/health"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()
        
    async def get_order_details(self, order_id: str) -> dict:
        url = f"{self.base_url}/api/support/orders/{order_id}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()
        
    async def get_payment_status(self, order_id: str) -> dict:
        url = f"{self.base_url}/api/support/orders/{order_id}/payment"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()
        
    async def get_shipment_status(self, order_id: str) -> dict:
        url = f"{self.base_url}/api/support/orders/{order_id}/shipment"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()