# StegSports Partnerize Credential Boundary Mirror Handoff

## Source of truth

This file is the canonical continuation record for the StegSports-CFP Partnerize provider credential boundary.

## Finding

Current source contained two independent consumer-side Partnerize credential paths:

```text
api/app/partnerize_client.py
  PARTNERIZE_APP_KEY
  PARTNERIZE_USER_API_KEY
  Basic Authorization construction
  direct httpx provider execution

api/app/routes_partnerize.py
  PARTNERIZE_APP_KEY
  PARTNERIZE_API_KEY
  Basic Authorization construction
  direct httpx provider execution
```

This conflicts with TV/TVC-only credential-bearing provider processing.

SeatGeek/StubHub ticket-link code is not included in this finding: it constructs public web URLs and optional affiliate identifiers and does not authenticate a provider API.

## Required repair

```text
credential authority: TV/TVC
StegSports provider credential authority: NONE
Partnerize key environment reads: RETIRED_ON_BRANCH
Basic Authorization construction: RETIRED_ON_BRANCH
direct Partnerize provider execution: RETIRED_ON_BRANCH
replacement state: TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED
provider runtime: NOT OBSERVED
authority_effect: NONE
```

No replacement broker, OAuth path, credential store, provider runtime, settlement authority, or publication authority is authorized.

## Collision boundary

This lane owns:
- `api/app/partnerize_client.py`
- `api/app/routes_partnerize.py`
- `tests/test_partnerize_credential_boundary.py`
- this handoff
- bounded README credential wording

It does not change ticket affiliate-link generation, SeatGeek/StubHub public search URL construction, click analytics, or unrelated sports application logic.

## Lifecycle

```text
source repair: IMPLEMENTED_ON_BRANCH
validation: PENDING
merge: PENDING
TVC Partnerize route: NOT PROVEN
provider execution: NOT OBSERVED
```
