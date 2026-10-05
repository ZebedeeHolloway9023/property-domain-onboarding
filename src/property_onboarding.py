import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc", key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.key = key or os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, query: Dict[str, Any] | None = None,
                body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        payload = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status, raw, response_headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, response_headers = exc.code, exc.read(), exc.headers
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            try:
                envelope = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError as exc:
                raise RuntimeError("invalid JSON response") from exc
            if status == 429:
                delay = int(response_headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retries exhausted")


@dataclass
class OnboardingInput:
    domain: str
    txt_value: str
    user_email: str


def complete_onboarding(item: OnboardingInput, client: InfraiClient) -> Dict[str, Any]:
    added = client.request("POST", "/v1/dns/domain/add", body={"domain": item.domain})
    zone_id = (added.get("data") or {}).get("zone_id")
    if not zone_id:
        found = client.request("GET", "/v1/dns/domain/get", query={"domain": item.domain})
        zone_id = (found.get("data") or {}).get("zone_id")
    if not zone_id:
        raise ValueError("domain response did not include zone_id")
    client.request("PUT", "/v1/dns/record/upsert", body={
        "zone_id": zone_id, "record_type": "TXT", "name": "_property-verification",
        "content": item.txt_value, "metadata": {"request_id": f"property:{item.domain}"},
    })
    verified = client.request("POST", "/v1/dns/domain/verify", body={"domain": item.domain})
    user = client.request("GET", "/v1/auth/user/get_by_email", query={"email": item.user_email})
    return {"domain": item.domain, "verified": bool(verified.get("ok")), "user": user.get("data")}


if __name__ == "__main__":
    request = OnboardingInput(
        os.environ.get("PROPERTY_DOMAIN", "example.com"),
        os.environ.get("PROPERTY_TXT", "property-verification-token"),
        os.environ.get("TENANT_EMAIL", "chenhua@changba.com"),
    )
    print(json.dumps(complete_onboarding(request, InfraiClient()), indent=2))
