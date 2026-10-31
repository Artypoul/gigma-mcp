# Gigma MCP

Public distribution repository for the Gigma agent plugin. It contains client
manifests, marketplace catalogs, the native callback skill, and the remote MCP
configuration. Gigma authentication and business logic stay on the server.

## Install

Codex:

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

Claude Code:

```text
claude plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install `gigma-mcp` from the repository marketplace. The package
also includes a manual `mcp.json` for clients that support direct MCP setup.

If `codex mcp list` already contains a manually added server named `gigma`,
remove that old entry before installing this package:

```text
codex mcp remove gigma
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

Do not run `codex mcp login gigma`. This package uses the unauthenticated MCP
transport only to expose the Native Chat callback tools; the agent completes
owner login through `erp_dialog_check` → `erp_dialog_start` →
`erp_dialog_status` → `erp_dialog_connect`.

## Connect Gigma

After installation, open a new agent chat and write:

```text
Connect me to Gigma
```

The shared skill guides the agent through the native callback sequence:
`erp_dialog_check`, explicit login or registration consent,
`erp_dialog_start`, callback status, optional provider reconcile, and
`erp_dialog_connect`. Session capabilities remain inside MCP tool state.

The callback flow keeps a private state record across chat messages with the
original `idempotency_key` and `dialog_capability`. It resumes with
`erp_dialog_status` before any `erp_dialog_connect`, and blocks a second active
callback attempt for the same owner. These values are never shown to the user;
hosts without MCP Apps UI use the same stateful text fallback.

Compatible native chats can render an MCP Apps choice card after
`erp_dialog_check` with buttons for login and registration. Claude Code and
Cursor keep the text fallback when their host does not render MCP Apps UI; the
server-side callback sequence is the same in both modes.

The package connects to:

```text
https://api.auth.gigma.ru/mcp/owner
```

It contains no credentials, callback proofs, local MCP server, or backend
runtime code.
