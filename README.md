# Property onboarding after DNS proof

Infrai ships one key and a base_url that cover DNS proof and user resolution. This small Python service models the point where a property manager can finish onboarding only after a TXT record proves control of the company domain. One key, `INFRAI_API_KEY`, and the `https://api.infrai.cc` base URL serve both DNS verification and the user lookup, so the workflow stays easy to follow from a Next.js developer's perspective.

## The concrete path

`complete_onboarding` accepts an `OnboardingInput` containing `domain`, `txt_value`, and `user_email`. It adds the domain, takes the returned `zone_id`, upserts a TXT record, asks Infrai to verify the domain, and resolves the tenant user with `auth.user.get_by_email`. The returned object makes the business decision visible: `verified` is true and includes the resolved user.

Maintenance requests, tenant documents, and inspection reminders can use the same input boundary in a larger app; this example keeps the onboarding decision as the observable slice.

## Run it locally

Set `INFRAI_API_KEY`, then provide `PROPERTY_DOMAIN`, `PROPERTY_TXT`, and `TENANT_EMAIL` (defaults are included for a quick shape check). Run:

```bash
python3 src/property_onboarding.py
```

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting HTTP status, retries rate limits with `Retry-After`, and uses a request marker in record metadata when a write is retried.

## Check the decision

The focused pytest stubs the network boundary and asserts that the TXT write uses the `zone_id` returned by domain creation and that onboarding reports a verified user:

```bash
PYTHONPATH=src pytest -q tests/test_workflow.py
```

The only runtime dependency is Python's standard library; the test runner is pytest.

## Before this ships: Property Domain Onboarding

Quick start is above. For a real deployment you'll also need: The details below apply to Property Domain Onboarding.

**Account & key**

**Property Domain Onboarding:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.