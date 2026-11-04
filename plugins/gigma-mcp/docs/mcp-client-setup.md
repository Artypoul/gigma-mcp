# Gigma MCP client setup

This guide covers the public plugin and its native owner callback flow. It does
not enable the server, change production flags, or replace the server's
OAuth/PKCE mode for confidential clients.

## Install

### Codex

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

If a manually configured server named `gigma` exists, remove that entry first:

```text
codex mcp remove gigma
```

Verify that the plugin and server are present:

```text
codex mcp list
```

Keep one `gigma` registration only. Close old Gigma chats and restart the
client after removing a manual entry or updating the plugin. Before connecting
an owner, run the read-only live contract check from either the installed plugin
directory (alongside its `README.md` and `mcp.json`) or the repository checkout root:

```text
python check_live_contract.py
```

The check must report a text-only contract. If the client still shows a choice
card, it is using stale or different metadata; do not answer the same choice in
text, and start a fresh client chat after cleanup.

Do not expect owner authentication at this point. Installation is not login.

### Claude Code

```text
claude plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
claude plugin install gigma-mcp@gigma-mcp
```

### Cursor

Install `gigma-mcp` from the repository marketplace, or add the package's
`plugins/gigma-mcp/mcp.json` through Cursor MCP settings.

## Native owner login

Start a new agent chat and write:

```text
Connect me to Gigma
```

The agent asks for the owner phone. Do not paste a token, password, callback
proof, or capability.

The expected sequence is:

```text
erp_dialog_check
→ one explicit text login/register choice
→ erp_dialog_start
→ callback call from the same phone
→ erp_dialog_status
→ one erp_dialog_connect
→ erp_dialog_me
```

After `erp_dialog_check`, ask the login/register question once and call
`erp_dialog_start` only after explicit textual consent. Registration asks for
a project name. Login does not. A host approval for the project check is not
the login/register choice. If a choice card appears, stop, report the metadata
mismatch and clean up the client registration before another attempt.

The callback state spans multiple chat messages. The agent keeps opaque state
inside MCP tool state. If the host loses that state, the agent must not ask for
the capability; it must report that a fresh check or bounded recovery is needed.

## Text callback flow and transport OAuth mode

The package transport uses the slash route
`https://api.auth.gigma.ru/mcp/owner/` to avoid a POST redirect. This
package's Codex mapping uses `auth.type: none` so the native dialog tools can
be discovered without a pasted token. Do not run `codex mcp login gigma` in the
same attempt.

All clients use the same text callback tools and textual consent step. This
package expects a text-only backend contract and does not execute a UI choice.

The live server may advertise host-managed OAuth in its initialization
instructions. That is a separate mode for confidential clients with different
client metadata, redirect, consent, grant and revocation rules. It is not a
second step in the native callback flow.

If the installed client requires OAuth before it exposes `erp_dialog_*`, stop
and report a transport contract mismatch. Do not replace the flow with REST, a
guessed endpoint, or a second OAuth attempt.

## Server availability

The server controls whether the owner MCP is enabled. The plugin cannot turn on
server flags. A successful installation does not prove that the live endpoint
is enabled, that callback delivery works, or that production is ready.

## First successful session

After `erp_dialog_connect`, the agent should call `erp_dialog_me`, explain the
workspace in plain language, and offer:

- applications;
- subscription catalog and plans;
- subscriptions;
- payment review;
- counterparty investigation;
- activity logs;
- disconnect.

## Troubleshooting

Use [the troubleshooting guide](mcp-troubleshooting.md) for expired callbacks,
lost state, rate limits, unknown outcomes, disabled transport and OAuth/native
mismatch.
