# Gigma MCP client setup

This guide covers the public plugin and its native owner callback flow. It does
not enable the server, change production flags, or replace the server's
OAuth/PKCE mode for confidential clients.

## Install

### ChatGPT web

Follow [the ChatGPT setup guide](chatgpt-setup.md). Install the portable private
plugin or add the existing HTTPS MCP endpoint using ChatGPT's custom-server
flow. Select transport authentication **None** for this native callback
contract. The owner still authenticates through the callback tools.

Codex marketplace commands do not configure ChatGPT web. Check the actual
discovered tools in the ChatGPT conversation before beginning callback login;
the presence of a skill or plugin card alone is not sufficient.

### Codex

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

The plugin declares `gigma` in its root `mcp.json`. A compatible client registers
that MCP connection when the plugin is installed and enabled, alongside its
skills. Do not add a second server with `codex mcp add`.

If a manually configured server named `gigma` exists, remove that entry first:

```text
codex mcp remove gigma
```

Keep one `gigma` registration only. Close old Gigma chats and restart the
client after removing a manual entry or updating the plugin. Inspect the plugin's
MCP connection in the client and confirm that the new chat exposes
`erp_dialog_check`, `erp_dialog_start`, `erp_dialog_status`, `erp_dialog_connect`
and `erp_dialog_me`. Skills alone do not confirm server registration.
Before connecting an owner, run the read-only live contract check from either
the installed plugin directory (alongside its `README.md` and `mcp.json`) or the
repository checkout root:

```text
python check_live_contract.py
```

The check must report a text-only contract. If the client still shows a choice
card, it is using stale or different metadata; do not answer the same choice in
text, and start a fresh client chat after cleanup.

Do not expect owner authentication at this point. Installation is not login.

For an update from 0.3.0, install 0.3.1 of the existing plugin. Version 0.3.0
placed an `extensions` field in the portable server entry; the inspected
[Codex parser](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
rejects that field and can omit the MCP server while loading the skills.
Version 0.3.1 removes it, fixing this parser compatibility issue without changing
the native callback flow. Confirm tool discovery in the installed client before
starting owner login.

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

The agent asks for the owner phone only if it is not already known. Do not paste
a token, password, callback proof, or capability.

When an existing session capability is in MCP tool state and the discovered
check schema supports it, the agent includes it in a new check. An authenticated
result continues that session without a login/register question. If the schema
does not support it, the agent uses the legacy phone/key check below. On
`not_authorized` or `operation_unavailable`, it stops without retrying the check
without the capability or starting a callback.

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

For a newly prepared result with no prior start, ask the login/register question
once and call `erp_dialog_start` only after explicit textual consent. Registration asks for
a project name. Login does not. A host approval for the project check is not
the login/register choice. If a choice card appears, stop, report the metadata
mismatch and clean up the client registration before another attempt.

For an exact check retry, retain the same key and arguments. While a callback is
pending, normally check the same callback's status instead of starting another.
If an exact replay follows a start that was sent or may have been sent, check
the original stored dialog capability's status before a consent decision; if
it is unavailable, use bounded recovery. A different returned capability does
not settle the original attempt or justify a new start. When start's outcome is unknown,
`awaiting_choice` does not prove the provider was not called: use bounded
recovery without an automatic start or fresh consent. Preserve earlier consent
for an unchanged decision. A pending callback for a different identity does not
connect the new target.

The callback state spans multiple chat messages. The agent keeps opaque state
inside MCP tool state. If the host loses that state, the agent must not ask for
the capability; it must report that a fresh check or bounded recovery is needed.

## Text callback flow and transport OAuth mode

The package transport uses the slash route
`https://api.auth.gigma.ru/mcp/owner/` to avoid a POST redirect. The server permits
native dialog discovery without credentials. The portable server entry declares
only the transport type and URL. Select transport authentication **None** if the
host's connection flow asks for it; do not embed credentials or per-server auth
extensions in this config. Do not run `codex mcp login gigma` in the same attempt.

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
