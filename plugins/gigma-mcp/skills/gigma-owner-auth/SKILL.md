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

After a successful connection, call `erp_dialog_me` before business tools and
explain the workspace/application summary in plain language.

## Native callback sequence

When the user asks to connect an owner workspace:

1. Ask for the owner phone and create a cryptographically secure
   `idempotency_key` matching `[A-Za-z0-9_-]{32,128}`. Call
   `erp_dialog_check`.
2. Present the `project_exists` result and ask the user to choose login or
   registration. Do not infer consent from that result. Ask for a project name
   only if the user chooses registration. Call `erp_dialog_start` only after
   explicit consent with `consent: true`; login omits `project_name`.
3. Show the callback number returned by the tool and ask the user to call it
   from the phone they supplied. Keep the same idempotency key only for an exact
   phone/check retry.
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
  is valid only for this MCP session and business tools.
- After the work is complete, call `erp_dialog_logout` when the user asks to
  disconnect, discard the capability, and stop calling business tools.

Use the server's discovered schemas and bounded error codes as the source of
truth. Keep write operations behind the agent's normal approval prompt.
