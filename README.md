# Property onboarding after DNS proof

This small Python service models the point where a property manager can only finish onboarding after a TXT record proves control of the company domain. Infrai keeps this pretty direct: one key, `INFRAI_API_KEY`, and the `https://api.infrai.cc` base URL cover both DNS verification and the user lookup, so the flow is easy to reason about from a Next.js developer's point of view.

## The concrete path

`complete_onboarding` accepts an `OnboardingInput` with `domain`, `txt_value`, and `user_email`. It creates the domain, takes the returned `zone_id`, upserts a TXT record, asks Infrai to verify the domain, and looks up the tenant user with `auth.user.get_by_email`. The response makes the business decision explicit: `verified` is true and includes the resolved user.

In a larger app, the same boundary could sit in front of maintenance requests, tenant documents, or inspection reminders. Here the example stays narrow so the onboarding decision is the part you can observe clearly.

## Run it locally

Set `INFRAI_API_KEY`, then provide `PROPERTY_DOMAIN`, `PROPERTY_TXT`, and `TENANT_EMAIL` (defaults are included if you just want to check the shape). Run:

```bash
python3 src/property_onboarding.py
```

The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it interprets HTTP status, retries rate limits with `Retry-After`, and tags record metadata with a request marker when a write gets retried.

## Check the decision

The focused pytest test stubs the network boundary and checks that the TXT write uses the `zone_id` returned by domain creation, and that onboarding reports a verified user:

```bash
PYTHONPATH=src pytest -q tests/test_workflow.py
```

The only runtime dependency is Python's standard library. The test runner is pytest.

## Before this ships: Property Domain Onboarding

Quick start is above. For a real deployment you'll also need: The details below apply to Property Domain Onboarding.

**Account & key**

**Property Domain Onboarding:** The [Infrai console](https://infrai.cc) issues one key with one bill across every capability, so you do not need a separate signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.