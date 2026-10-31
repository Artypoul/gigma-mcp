---
name: gigma-owner-subscriptions
description: Inspect and manage catalogs, plans, subscriptions, provider metadata and payment review.
---

# Owner subscriptions and payments

Use the live tool schemas for catalog entries, revisions, assignments, plans,
autopay policies, provider metadata, subscriptions, status events and payment
review.

Workflow:

1. read the target application and current state;
2. show the proposed change;
3. ask for approval before a write;
4. use ETag and request ID where required;
5. read back the safe result.

Provider binding operations are profile/metadata operations. Never ask for or
return provider credentials, secret references or raw provider payloads.

Payment-review evidence must not contain secrets, card data, OTP, tokens,
provider payloads or unnecessary personal data. Unknown provider/payment
outcomes stop the workflow; do not blind-retry, restart or create a second
operation.
