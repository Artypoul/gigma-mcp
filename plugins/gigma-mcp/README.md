# Gigma MCP agent plugin

This package connects ChatGPT, Codex, Claude Code, and Cursor to the existing Gigma owner
MCP at `https://api.auth.gigma.ru/mcp/owner/`. It packages the remote
Streamable HTTP server configuration and skills for the native callback flow
and owner operations. Authentication and business logic remain on the Gigma
server.

## Install

### ChatGPT

Install the complete portable package through Plugin Creator, or add the
remote server in **Plugins → + → Add custom MCP server** with URL
`https://api.auth.gigma.ru/mcp/owner/` and authentication **None**. The complete
package includes six workflow skills; a direct server connection supplies tools.
Use [the ChatGPT guide](docs/chatgpt-setup.md) to verify the connection and avoid
duplicate registrations. A local Codex marketplace install does not register a
connection in ChatGPT web. A successful upload is not proof that tools were
discovered or that an owner session exists.

The complete plugin declares `gigma` in `mcp.json`. A compatible client registers
that connection with the skills when the plugin is installed and enabled;
complete any connection steps presented by the host. You do not need to add
the same MCP endpoint separately.

### Codex, Claude Code and Cursor

Install from the public marketplace repository:

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

The plugin supplies the MCP configuration automatically.
Keep exactly one `gigma` registration in the active client. If an old manual entry exists,
remove it, close old Gigma chats and restart the client. Check that the plugin's
MCP connection and `erp_dialog_*` tools are available. Verify the live server
contract separately with `python check_live_contract.py`.
Run that command from this installed plugin directory, which contains
`README.md`, `mcp.json` and the bundled [checker](check_live_contract.py).
The checker also runs from the root of a repository checkout.

Claude Code:

```text
claude plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install the `gigma-mcp` entry from the repository marketplace or
use the package's `mcp.json` in Cursor MCP settings.

For the complete first-run procedure, read
[docs/mcp-client-setup.md](docs/mcp-client-setup.md).

Version 0.3.1 fixes the 0.3.0 configuration that allowed skills to load while
the [Codex portable parser](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
rejected the MCP entry's unsupported `extensions` field. The portable server
entry now contains only the transport type and URL. This parser fix does not
by itself verify host provisioning or sign an owner in; the native callback
flow is unchanged.

## Native owner connection

An authenticated session can be reused when the discovered check schema supports
it. When a new login is needed and a check prepares a callback, the package uses
one callback choice path at a time:

`erp_dialog_check` → explicit text login/registration choice →
`erp_dialog_start` → callback call → `erp_dialog_status` →
`erp_dialog_connect`.
All clients use the text callback flow.

The agent shows only the callback number and safe project results. Opaque
dialog and session capabilities remain in MCP tool state. They are never
copied into chat, URLs, logs, files, or another service.

Do not run `codex mcp login gigma` for this native flow. The server exposes
native dialog discovery without credentials. Select transport authentication
**None** if the host's connection flow asks for it; no credentials or per-server
authentication extension are embedded in the portable MCP entry. The package
uses the slash
transport route `https://api.auth.gigma.ru/mcp/owner/` to avoid a POST
redirect. The live server may advertise host-managed OAuth for other
confidential transport clients. If the active host requires OAuth before
exposing `erp_dialog_*`, stop and report a transport contract mismatch instead
of mixing OAuth with the callback attempt.

The public package does not advertise or depend on optional UI card. If a client
still renders a UI card while the live contract is text-only, the client is
using stale or different registration metadata; restart it and do not answer
the same choice twice.

## After connection

The agent first reads the safe owner/workspace summary and then offers:

- applications and service-client metadata;
- subscription catalog, plans and revisions;
- subscriptions and status events;
- payment-provider metadata and payment-review cases;
- counterparty investigation and activity logs.

Writes require the normal approval prompt. Credentials, provider secrets,
logo uploads and other confidential HTTP operations are not moved into chat.

Read [the project workflow guide](docs/gigma-project-workflows.md),
[the capability matrix](docs/mcp-capability-matrix.md), and
[the troubleshooting guide](docs/mcp-troubleshooting.md).

The package does not contain credentials, callback proofs, a local MCP server,
or a second implementation of the Gigma authentication flow.
