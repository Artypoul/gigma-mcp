---
name: gigma-owner-auth
description: Connect to the Gigma owner MCP with the native callback flow.
---

# Gigma owner MCP

Use the `gigma` MCP server for owner workspace operations. The server already
implements the callback flow; do not call a REST endpoint or create a second
authentication path.

## What the user sees

Tell the user why the phone is needed and that no token, password, or callback
proof must be pasted. Show only the callback number and safe project results.
Never show `dialog_capability`, `session_capability`, or the generated
idempotency key.

After a new callback connection, call `erp_dialog_me` before business tools and
explain the workspace/application summary in plain language.

## Native callback sequence

When the user asks to connect an owner workspace:

1. If the same callback is already pending, normally use `erp_dialog_status`
   with its existing dialog capability; do not start a second callback. A
   pending callback for another identity does not connect the new target. For a new
   check, ask for the owner phone only if it is not already known and create a
   cryptographically secure `idempotency_key` matching `[A-Za-z0-9_-]{32,128}`.
   If a session capability is in MCP tool state and the discovered
   `erp_dialog_check` input schema advertises `session_capability`, pass it
   with the phone and key. Otherwise use the legacy phone/key check. Call
   `erp_dialog_check` with those arguments.
   For an exact check retry, retain the same key and all the same arguments.
2. If the check returns `authenticated: true`, continue with that existing
   session capability and the requested work; do not ask for login or
   registration or start a callback. On `not_authorized` or
   `operation_unavailable`, stop and report the error; do not retry without
   the capability or start a new callback. If an exact replay follows a start
   that was sent or may have been sent, call `erp_dialog_status` on the original
   stored dialog capability before any consent decision. If it is unavailable,
   use the existing bounded recovery rules. A different capability returned by
   the replay does not settle the original attempt or justify a new start.
   Continue the original attempt;
   do not ask for consent again or start another callback. If start's outcome
   is unknown, `awaiting_choice` does not prove that the provider was not
   called: use the existing bounded recovery rules, without automatic start or
   fresh consent. Preserve prior consent for an unchanged decision. Only for
   a newly prepared result where no start was sent, containing `project_exists`,
   `dialog_capability`, and `expires_at`, use exactly one consent path: the
   text callback flow.
   Present the `project_exists` result and ask the user to choose login or
   registration once. Do not infer consent from that result. Ask for a project
   name only if the user chooses registration, and call `erp_dialog_start`
   only after explicit textual consent with `consent: true`; login omits
   `project_name`. A generic host approval for `erp_dialog_check` is not this
   choice. If UI metadata or a choice card appears, stop and report stale or
   incompatible transport metadata; do not use the card or start a second path.
3. After `erp_dialog_start` returns, show its callback number and ask the user
   to call it from the phone they supplied. A prepared `erp_dialog_check`
   returns project state and dialog capability, not the callback number.
4. Poll `erp_dialog_status` with the returned dialog capability using bounded
   waits and visible progress. Do not start another callback while the current
   one is pending. The status call is read-only. Use
   `erp_dialog_reconcile` only after the user explicitly asks to resolve an
   uncertain provider result.
5. Call `erp_dialog_connect` once verification is ready. If its response is
   lost, call status first and allow one deliberate recovery connect. Stop on
   `recovery_required`.
6. After connect, call `erp_dialog_me`, show a safe workspace summary, and ask
   what the user wants to do next.

Keep the dialog/session state across messages. If the host loses the opaque
capability, do not ask the user to paste it: let the old attempt reach its
terminal state or report that a fresh check is required.

If the user declines, the callback is stale, or the server returns `expired` or
`cancelled`, report it. A changed login/registration choice, project name, or
expired attempt requires finishing the old dialog and a new check with a new
idempotency key. On `provider_outcome_unknown` or `recovery_required`, stop
and report the bounded state; do not auto-cancel, reconcile, restart, or issue a
second session. Reconcile, cancel, or a new attempt require an explicit user
decision.

When the user explicitly cancels an unfinished attempt, call
`erp_dialog_cancel` and treat the dialog as terminal.

## Capability and privacy rules

- Treat `dialog_capability`, `session_capability`, and the idempotency key as
  credentials. Never repeat them in chat, logs, summaries, URLs, files, or
  telemetry.
- Never ask the user to paste a token or callback proof.
- Do not put a workspace identifier in a tool argument to switch tenants. The
  server derives the workspace from the verified callback session.
- Do not mix this native flow with OAuth/PKCE (`codex mcp login` or an
  equivalent host flow) in the same attempt. OAuth is a separate host-managed
  mode.
- The dialog capability is valid only for dialog tools; the session capability
  is valid only for this MCP session and business tools, and for
  `erp_dialog_check` when its discovered schema advertises that argument.
- After the work is complete, call `erp_dialog_logout` when the user asks to
  disconnect, discard the capability, and stop calling business tools.

Use the server's discovered schemas and bounded error codes as the source of
truth. Keep destructive and business-state writes behind the agent's normal
approval prompt. `erp_dialog_check` is non-destructive: it can reuse an
authenticated session or prepare short-lived dialog state before consent.
