# Gigma MCP agent plugin

This package connects Codex, Claude Code, and Cursor to the existing Gigma MCP
at `https://api.auth.gigma.ru/mcp/owner`. It packages the remote
Streamable HTTP server configuration and a shared skill for the native callback
flow. The authentication and business logic remain on the Gigma server.

## Install from this repository

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

Cursor can install the `gigma-mcp` entry from the repository marketplace.
For a manual setup, use the package's `mcp.json` in the Cursor MCP settings.

## What the agent does after installation

The plugin is named `gigma-mcp`; its bundled MCP server keeps the canonical
server id `gigma`. The Codex manifest marks the connection as `auth.type:
none`: Native Chat callback is performed by MCP tools, not by host-managed
OAuth.

The shared `gigma-owner-auth` skill teaches the agent to call
`erp_dialog_check`, `erp_dialog_start`, `erp_dialog_status`, and
`erp_dialog_connect`, then use the opaque session capability for business
tools. It also covers cancellation and logout. Capabilities remain inside MCP
tool state and are never copied into user-facing text. Hosts may prefix MCP
tool names with their plugin namespace; use the discovered schema and tool
name from the active client.

Compatible native chats may render an MCP Apps choice card after
`erp_dialog_check`. Claude Code and Cursor keep the text fallback when their
host does not render MCP Apps UI; both paths call the same server-side
`erp_dialog_start` contract.

The package does not contain credentials, callback proofs, a local MCP server,
or a second implementation of the Gigma authentication flow.
