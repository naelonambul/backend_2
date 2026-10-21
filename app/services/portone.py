from typing import Any
from urllib.parse import quote

import httpx


class PortOneError(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class PortOneClient:
    BASE_URL = "https://api.portone.io"

    def __init__(self, api_secret: str, timeout: float = 5.0):
        if not api_secret.strip():
            raise ValueError("PortOne API secret is required")
        self._authorization = f"PortOne {api_secret}"
        self._timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": self._authorization, "Accept": "application/json"}
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
        try:
            response = httpx.request(
                method,
                f"{self.BASE_URL}{path}",
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise PortOneError("PortOne request timed out", retryable=True) from exc
        except httpx.RequestError as exc:
            raise PortOneError("PortOne request failed", retryable=True) from exc

        if response.status_code >= 500:
            raise PortOneError("PortOne service is unavailable", retryable=True)
        if response.is_error:
            raise PortOneError("PortOne rejected the request")
        try:
            data = response.json()
        except ValueError as exc:
            raise PortOneError("PortOne returned an invalid response") from exc
        if not isinstance(data, dict):
            raise PortOneError("PortOne returned an invalid response")
        return data

    def get_payment(self, payment_id: str) -> dict[str, Any]:
        payment = self._request("GET", f"/payments/{quote(payment_id, safe='')}")
        amount = payment.get("amount")
        if (
            not isinstance(payment.get("id"), str)
            or not isinstance(payment.get("status"), str)
            or not isinstance(amount, dict)
            or type(amount.get("total")) is not int
            or not isinstance(payment.get("currency"), str)
        ):
            raise PortOneError("PortOne returned an invalid payment")
        return payment

    def cancel_payment(self, payment_id: str, reason: str) -> dict[str, Any]:
        response = self._request(
            "POST",
            f"/payments/{quote(payment_id, safe='')}/cancel",
            json={"reason": reason},
        )
        cancellation = response.get("cancellation")
        if not isinstance(cancellation, dict) or not isinstance(cancellation.get("status"), str):
            raise PortOneError("PortOne returned an invalid cancellation")
        return response
