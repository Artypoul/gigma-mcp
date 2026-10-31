---
name: gigma-owner-investigation
description: Read redacted counterparty and activity evidence inside the verified workspace.
---

# Owner investigation

Use `erp_counterparty_investigate` and `erp_activity_logs_inspect` for
read-only investigation.

- Use the selector required by the active schema.
- If identity resolution is ambiguous, stop without choosing the first match.
- Keep opaque continuation tokens inside the operation.
- Preserve the bound page size and filters.
- Distinguish confirmed and possible relationships.
- Report coverage gaps instead of synthesizing missing ERP history.

Never return contacts, OTP, hashes, tokens, callback proofs, credentials, raw
provider payloads or free-text evidence.
