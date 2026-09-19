# StegSports-CFP
CFP Championship bound.


## Provider credential boundary

Authenticated Partnerize operations are not executed in StegSports-CFP and no Partnerize provider keys are consumer credentials. The historical direct provider path fails closed with `TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED` until an already-admitted TV/TVC route returns bounded non-secret results. Public SeatGeek/StubHub affiliate/search-link generation remains separate and does not confer provider API credential authority.

Canonical handoff: `docs/STEGSPORTS_PARTNERIZE_CREDENTIAL_BOUNDARY_MIRROR_HANDOFF.md`.


## Host-provider independence

The CFP dashboard no longer carries a default hosted SCW origin. `window.CFP_API_BASE` must be supplied explicitly by the admitted StegVerse runtime; absence fails closed with `CFP_API_BASE_NOT_CONFIGURED`.
