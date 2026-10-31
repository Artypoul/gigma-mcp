# Native callback choice buttons

## Intent

After `erp_dialog_check` finds an existing Gigma project, the user should be
able to choose login or registration with two visible buttons in a compatible
native chat. Claude Code and Cursor must keep working through the existing
textual skill flow when their host does not render MCP Apps UI.

## Current state

- `gigma-mcp` already exposes the remote owner MCP and the shared
  `gigma-owner-auth` skill.
- `erp_dialog_check` returns the existing callback projection and
  `dialog_capability`; `erp_dialog_start` remains the only operation that
  starts login or registration after explicit consent.
- The owner MCP uses FastMCP 1.30.0 and a strict custom tool registry. It does
  not currently register MCP Apps resources or tool UI metadata.
- The callback state machine, consent validation, idempotency rules, and
  capability boundaries are already implemented on the server and stay the
  source of truth.

## Chosen approach

The owner MCP will register one versioned static MCP Apps resource, for example
`ui://gigma/owner-auth/v1.html`, with MIME type
`text/html;profile=mcp-app`. The `erp_dialog_check` tool descriptor will point
to that resource through `_meta.ui.resourceUri`.

Because the service is pinned to FastMCP/mcp 1.30.0, which does not expose the
MCP Apps extension in its default initialization capabilities, the owner MCP
will add the standard `io.modelcontextprotocol/ui` capability with the same
MIME type at initialization. This is a narrow compatibility adapter; upgrading
the whole service to MCP 2.x is outside this feature.

The component will render an inline choice card with:

- `Войти в существующий проект` → call `erp_dialog_start` with `action=login`;
- `Зарегистрировать новый проект` → ask for the project name inside the card,
  then call `erp_dialog_start` with `action=register`.

The component will call tools through the MCP Apps host bridge. It will keep
the opaque dialog capability only in in-memory component state, never render
or log it, and send `consent: true` only after the user presses a button. The
existing normal tool projection remains available for text-only fallback; the
UI adds no second credential or callback path.
The server continues to validate the capability, action, project name, and
consent with the existing strict DTO.

The normal tool result and `gigma-owner-auth` skill remain unchanged as the
fallback. A host that ignores `_meta.ui.resourceUri` will show the existing
project result and the agent will ask the same login/registration question in
text. No host-specific branch or OAuth flow is added.

## Alternatives considered

1. **Codex-only plugin UI.** This would avoid changing the owner MCP, but
   Claude and Cursor would keep a different text-only experience. It does not
   satisfy the shared MCP contract.
2. **A new REST or callback endpoint for the buttons.** This would duplicate
   the existing state machine and widen the credential surface. It is rejected;
   the UI calls the existing MCP tools.
3. **MCP Apps resource with text fallback.** This keeps one server contract,
   gives compatible hosts native buttons, and preserves behavior everywhere
   else. This is the selected approach.

## Scope

In scope:

- owner MCP resource registration and tool metadata;
- a small dependency-free MCP Apps component for the choice step;
- package documentation and fallback instructions;
- focused server, resource, metadata, and package validation tests.

Out of scope:

- changing callback storage, provider delivery, consent semantics, or OAuth;
- buttons for callback polling, reconcile, connect, logout, or business tools;
- changing Claude/Cursor host implementations;
- production deploy or server configuration changes.

## Done when

1. `tools/list` advertises the UI resource on `erp_dialog_check` without
   exposing credentials in metadata.
2. `resources/read` serves the versioned component with the MCP Apps MIME type.
3. A compatible host can choose login or registration and the component calls
   the existing `erp_dialog_start` contract with explicit consent.
4. A host without MCP Apps UI still follows the current text fallback.
5. Focused tests and package validators pass on the exact PR head.
