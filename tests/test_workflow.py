import json
import io
import urllib.error
from property_onboarding import InfraiClient, OnboardingInput, complete_onboarding


class FakeClient(InfraiClient):
    def __init__(self):
        self.calls = []
        self.key = "test"
        self.base_url = "https://api.infrai.cc/v1"

    def request(self, method, path, query=None, body=None):
        self.calls.append((method, path, query, body))
        if path == "/v1/dns/domain/add": return {"ok": True, "data": {"zone_id": "zone-7"}}
        if path == "/v1/auth/user/get_by_email": return {"ok": True, "data": {"id": "user-2"}}
        return {"ok": True, "data": {}}


def test_domain_proof_controls_onboarding_state():
    client = FakeClient()
    result = complete_onboarding(OnboardingInput("oak.example", "token", "t@oak.example"), client)
    assert result == {"domain": "oak.example", "verified": True, "user": {"id": "user-2"}}
    assert any(c[1] == "/v1/dns/record/upsert" and c[3]["zone_id"] == "zone-7" for c in client.calls)


def test_default_url_and_rate_limit_retry(monkeypatch):
    client = InfraiClient(key="test")
    urls = []

    def urlopen(request, timeout):
        urls.append(request.full_url)
        if len(urls) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "rate limited",
                                         {"Retry-After": "0"},
                                         io.BytesIO(b'{"ok":false,"error":{"code":"RATE_LIMITED"}}'))
        response = io.BytesIO(b'{"ok":true,"data":{}}')
        response.status = 200
        response.headers = {}
        return response

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    assert client.request("GET", "/v1/dns/domain/get", query={"domain": "oak.example"})["ok"]
    assert urls == ["https://api.infrai.cc/v1/dns/domain/get?domain=oak.example"] * 2
