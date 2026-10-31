# Callback state persistence and single-flight guard

## Intent

Make the `gigma-owner-auth` client flow survive separate chat messages without
creating a second callback attempt. The agent must retain the opaque
`dialog_capability` and the original `idempotency_key`, resume with
`erp_dialog_status`, and call `erp_dialog_connect` only after the status is
ready.

## Goals

- Define one private state record for the active owner callback.
- Reuse the exact phone and idempotency key for check retries.
- Reuse the exact dialog capability for `start`, `status`, `reconcile`,
  `connect`, and `cancel`.
- Treat an active record as single-flight: do not call `check` or `start` for a
  second callback while the current record is pending.
- Recover a lost tool response by reading status first; never blindly retry a
  provider call or session issuance.
- Complete the verified path as `status` followed by one deliberate `connect`.

## Non-goals and constraints

- Do not expose, log, or ask the user to paste capabilities or idempotency keys.
- Do not add a REST endpoint, OAuth flow, local credential store, or second
  callback mechanism.
- Do not change server-side callback storage; the server remains authoritative
  for expiry, races, and session issuance.
- Keep the skill compatible with hosts that do not render MCP Apps UI.

## Approaches

1. **Skill state protocol (selected).** Extend the shared skill with a named
   private state record and explicit transition/guard rules, then validate the
   contract with the package validator. This changes the actual agent behavior
   without inventing a client runtime.
2. **Backend recovery lookup.** Add a server lookup keyed by phone or
   idempotency key. Rejected because it widens the credential surface and
   duplicates state already represented by the opaque capability.
3. **MCP Apps-only state.** Keep state in the HTML component. Rejected because
   Claude Code and Cursor text fallback would still lose state between
   messages.

## State protocol

The skill keeps a private `gigma_owner_callback` record containing the phone,
idempotency key, dialog capability, action, project name when present, and
lifecycle status. Values are never copied into user-facing text or logs.

- `check` creates the record only when no active record exists; a retry reuses
  the same key and phone.
- `start` is allowed once after explicit consent and stores the selected action.
- While status is pending, a new check/start is rejected locally with a bounded
  explanation; the agent polls `status` on the stored capability.
- `status` is read-only. `reconcile` is explicit only when requested.
- `connect` is called once after a verified/completed status and the returned
  session capability replaces the dialog record for business calls.
- Terminal, expired, cancelled, provider-unknown, or recovery-required states
  clear or quarantine the record according to the existing skill rules; a new
  attempt requires explicit user intent.

## Verification

Add validator assertions for the state-record terms, the single-flight guard,
the status-before-connect order, and the no-secret/no-OAuth rules. Run the
package validator, Ruff check/format, and the existing backend callback tests
that already prove server-side concurrent start/connect protection.
