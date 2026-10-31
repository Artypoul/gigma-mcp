---
name: gigma-owner-auth
description: Connect to the Gigma owner MCP with the native callback flow.
---

# Gigma owner MCP

Use the `gigma` MCP server for owner workspace operations. The server already
implements the callback flow; do not call a REST endpoint or create a second
authentication path.

## Native callback sequence

When the user asks to connect an owner workspace:

1. Ask for the owner phone and create a high-entropy `idempotency_key` matching
   `[A-Za-z0-9_-]{32,128}`. Call `erp_dialog_check`.
2. Present the `project_exists` result and ask the user to choose login or
   registration. Do not infer consent from that result. Ask for a project name
   only if the user chooses registration. Call `erp_dialog_start` only after
   explicit consent with `consent: true`; login omits `project_name`.
3. Show the callback number returned by the tool and ask the user to call it
   from the phone they supplied. Keep the same idempotency key for an exact
   phone/check retry.
4. Poll `erp_dialog_status` with the returned `dialog_capability` until the
   callback is verified or the server returns a terminal state. Do not start
   another callback while the current one is pending.
   `erp_dialog_status` is read-only. Use `erp_dialog_reconcile` only as an
   explicit provider check when the user asks to resolve an uncertain result.
5. Call `erp_dialog_connect` once verification is ready. Keep the returned
   `session_capability` in MCP tool state and pass it to the requested business
   tools; every no-bearer business call requires that capability. Use
   `erp_dialog_me` when the current owner/project summary is needed.

## Persistent callback state and single-flight guard

Keep one private `gigma_owner_callback` state record across chat messages. It
contains the supplied phone, the generated `idempotency_key`, the returned
`dialog_capability`, the selected `action`, the optional `project_name`, and
the current lifecycle `status` (plus the safe callback number and expiry when
returned). The record lives only in MCP tool state: never copy its values into
user-facing text, logs, URLs, or a new tool argument invented from memory.

- Create the record before `erp_dialog_check` and keep the same `idempotency_key`
  for an exact phone/check retry. Never generate a new key
  just because the conversation moved to a new message.
- Treat the record as single-flight. While it is active, reject a parallel callback attempt
  for the same or another phone; do not call a second
  `erp_dialog_check` or `erp_dialog_start` until the current record is
  terminal or the user explicitly chooses a new attempt after expiry/cancel.
- Store `dialog_capability` immediately after `check` and reuse it for
  `start`, `status`, `reconcile`, `connect`, and `cancel`. A lost response is
  not permission to create a fresh capability or callback.
- `status` is read-only and is the recovery operation. After `start`, on every
  new message resume with the stored capability and call `erp_dialog_status`
  first. Only when it returns a verified/completed state may the flow advance
  through **status → connect**.
- Make one deliberate `erp_dialog_connect` call after that status. If its
  response is lost, call status first and recover the persisted completion;
  never run parallel connect calls or blindly repeat a provider/session
  operation.
- On `expired`, `cancelled`, `provider_outcome_unknown`, or
  `recovery_required`, stop and report the bounded state. Clear or quarantine
  the record according to the terminal state and require explicit user intent
  before a new callback attempt.

If the user declines, the callback is stale, or the server returns a terminal
`expired` or `cancelled` state, report it. Expiry, an account-exists conflict,
or a changed login/registration choice or project name requires finishing the
old dialog and a new check with a new idempotency key. On
`provider_outcome_unknown` or `recovery_required`, stop and report that bounded
state; do not auto-cancel, reconcile, restart, or issue a second session.
Reconcile, cancel, or a new attempt require an explicit user decision.
When the user explicitly cancels an unfinished attempt, call
`erp_dialog_cancel` and treat the dialog as terminal.

If the `erp_dialog_connect` response is lost, call status first. One deliberate
connect may recover persisted completion; stop when the server returns
`recovery_required`. Never retry a provider call or one-time issuance blindly.

## Capability and privacy rules

- Treat `dialog_capability`, `session_capability`, and the idempotency key as
  credentials. Never repeat them in chat, logs, summaries, URLs, files, or
  telemetry.
- Never ask the user to paste a token or callback proof. The user only sees the
  callback number and the safe project result.
- Do not put a workspace identifier in a tool argument to switch tenants. The
  server derives the workspace from the verified callback session.
- Do not mix this native flow with OAuth/PKCE (`codex mcp login` or an equivalent
  host flow) in the same attempt. OAuth is a separate host-managed mode.
- The `dialog_capability` is valid only for dialog tools. The
  `session_capability` is valid only for this Gigma MCP's session and business
  tools; never send either value to another service or in an HTTP header.
- After the work is complete, call `erp_dialog_logout` with the active session
  capability when the user asks to disconnect, then discard the capability and
  stop calling business tools.

Use the server's discovered schemas and bounded error codes as the source of
truth. Keep write operations behind the agent's normal approval prompt.
