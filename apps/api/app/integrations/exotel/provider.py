import httpx
from app.core.config import settings
from app.integrations.call_base import CallProvider, CallRequest, CallResult


# Maps Exotel status strings → our internal status constants
EXOTEL_STATUS_MAP: dict[str, str] = {
    "queued":       "INITIATED",
    "in-progress":  "IN_PROGRESS",
    "ringing":      "RINGING",
    "completed":    "COMPLETED",
    "failed":       "FAILED",
    "busy":         "BUSY",
    "no-answer":    "NO_ANSWER",
    "canceled":     "CANCELLED",
}


class ExotelProvider(CallProvider):
    """
    Exotel Click-to-Call provider.

    How it works:
      1. POST /v1/Accounts/{sid}/Calls/connect with From (agent phone), To (lead phone),
         CallerId (ExoPhone), StatusCallback (our webhook URL + shared secret).
      2. Exotel calls the *agent* first (From).
      3. When the agent answers, Exotel bridges to *lead* (To).
      4. Status updates arrive at our StatusCallback webhook endpoint.

    Authentication: HTTP Basic Auth with API Key as username, API Token as password.
    No SDK required — plain httpx POST with form-data.
    """

    def __init__(self):
        self.api_key = settings.EXOTEL_API_KEY
        self.api_token = settings.EXOTEL_API_TOKEN
        self.account_sid = settings.EXOTEL_ACCOUNT_SID
        self.caller_id = settings.EXOTEL_CALLER_ID
        self.subdomain = settings.EXOTEL_SUBDOMAIN
        self._base_url = (
            f"https://{self.subdomain}/v1/Accounts/{self.account_sid}/Calls/connect"
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_token and self.account_sid)

    async def initiate_call(self, request: CallRequest) -> CallResult:
        """
        POST form-data to Exotel /Calls/connect.
        from_identifier = agent's phone number
        to_identifier   = lead's phone number
        """
        if not self.is_configured:
            return CallResult(
                success=False, call_id=None,
                status="FAILED", error="Exotel is not configured",
            )

        callback_url = (
            f"{settings.API_URL}/api/v1/webhooks/exotel/status"
            f"?secret={settings.EXOTEL_WEBHOOK_SECRET}"
        )

        data = {
            "From": request.from_identifier,
            "To": request.to_identifier,
            "CallerId": self.caller_id,
            "Record": "true",
            "StatusCallback": callback_url,
            "StatusCallbackEvents": "terminal,answered",
            "StatusCallbackContentType": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    self._base_url,
                    data=data,
                    auth=(self.api_key, self.api_token),
                )
                if resp.status_code in (200, 201):
                    body = resp.json()
                    call_data = body.get("Call", {})
                    sid = call_data.get("Sid")
                    raw_status = call_data.get("Status", "queued")
                    our_status = EXOTEL_STATUS_MAP.get(raw_status, "INITIATED")
                    return CallResult(success=True, call_id=sid, status=our_status, extra=call_data)
                else:
                    return CallResult(
                        success=False, call_id=None,
                        status="FAILED",
                        error=f"Exotel HTTP {resp.status_code}: {resp.text[:300]}",
                    )
            except httpx.ConnectError:
                return CallResult(
                    success=False, call_id=None,
                    status="FAILED", error="Cannot connect to Exotel API",
                )
            except httpx.TimeoutException:
                return CallResult(
                    success=False, call_id=None,
                    status="FAILED", error="Exotel API request timed out",
                )

    async def end_call(self, provider_call_id: str) -> bool:
        """
        Exotel v1 does not expose a direct "hangup call" REST endpoint.
        We mark it as CANCELLED in our DB. The actual call will complete
        naturally and Exotel will deliver a terminal status webhook.
        """
        return True

    async def get_call_status(self, provider_call_id: str) -> str:
        """
        GET /v1/Accounts/{sid}/Calls/{CallSid}.json
        Returns our mapped status string.
        """
        url = (
            f"https://{self.subdomain}/v1/Accounts/{self.account_sid}"
            f"/Calls/{provider_call_id}.json"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, auth=(self.api_key, self.api_token))
                if resp.status_code == 200:
                    raw_status = resp.json().get("Call", {}).get("Status", "")
                    return EXOTEL_STATUS_MAP.get(raw_status, "UNKNOWN")
            except Exception:
                pass
        return "UNKNOWN"

    def validate_webhook_secret(self, secret: str) -> bool:
        """
        Exotel does not sign webhooks like Twilio.
        We append ?secret=... to our StatusCallback URL and validate it here.
        """
        return bool(secret and secret == settings.EXOTEL_WEBHOOK_SECRET)
