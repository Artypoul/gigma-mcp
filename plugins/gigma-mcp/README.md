# Gigma MCP agent plugin

This package connects Codex, Claude Code, and Cursor to the existing Gigma owner
MCP at `https://api.auth.gigma.ru/mcp/owner`. It packages the remote
Streamable HTTP server configuration and skills for the native callback flow
and owner operations. Authentication and business logic remain on the Gigma
server.

## Install

Install from the public marketplace repository:

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

Claude Code:

```text
claude plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install the `gigma-mcp` entry from the repository marketplace or
use the package's `mcp.json` in Cursor MCP settings.

For the complete first-run procedure, read
[docs/mcp-client-setup.md](../../docs/mcp-client-setup.md).

## Native owner connection

The package uses a native callback flow:

`erp_dialog_check` → explicit login or registration choice →
`erp_dialog_start` → callback call → `erp_dialog_status` →
`erp_dialog_connect`.

The agent shows only the callback number and safe project results. Opaque
dialog and session capabilities remain in MCP tool state. They are never
copied into chat, URLs, logs, files, or another service.

Do not run `codex mcp login gigma` for this native flow. The Codex mapping uses
`auth.type: none` for native dialog discovery. The live server may advertise
host-managed OAuth for other confidential transport clients. If the active host
requires OAuth before exposing `erp_dialog_*`, stop and report a transport
contract mismatch instead of mixing OAuth with the callback attempt.

## After connection

The agent first reads the safe owner/workspace summary and then offers:

- applications and service-client metadata;
- subscription catalog, plans and revisions;
- subscriptions and status events;
- payment-provider metadata and payment-review cases;
- counterparty investigation and activity logs.

Writes require the normal approval prompt. Credentials, provider secrets,
logo uploads and other confidential HTTP operations are not moved into chat.

Read [the project workflow guide](../../docs/gigma-project-workflows.md),
[the capability matrix](../../docs/mcp-capability-matrix.md), and
[the troubleshooting guide](../../docs/mcp-troubleshooting.md).

The package does not contain credentials, callback proofs, a local MCP server,
or a second implementation of the Gigma authentication flow.
