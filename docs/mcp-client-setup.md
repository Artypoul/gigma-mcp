# Gigma MCP client setup

This guide covers the public plugin and its native owner callback flow. It does
not enable the server, change production flags, or replace the server's
OAuth/PKCE mode for confidential clients.

## Install from the GitHub marketplace

Use repository **https://github.com/Artypoul/gigma-mcp**. The marketplace is
`gigma-mcp`; the plugin selector is `gigma-mcp@gigma-mcp`. The entry resolves to
`plugins/gigma-mcp` and includes six skills plus one remote `gigma` MCP declaration.

### ChatGPT

In a workspace that supports marketplace imports, an admin opens **Admin →
Plugins → Add → Import marketplace**. Enter the repository URL, leave Path
empty, and use the default branch or `main`. Inspect the per-plugin import
result, then configure the installation policy and install **Gigma MCP**.
For updates use **Admin → Plugins → Marketplaces → selected marketplace →
Sync now**. See [the ChatGPT setup guide](chatgpt-setup.md) for details.

These are workspace-admin controls; personal-account availability can differ.
OpenAI also documents that imported plugins declaring MCP servers may be
**Desktop only**, even with an HTTPS endpoint. A repository import does not
by itself confirm web tool availability or an owner session. See
[OpenAI's plugin management guide](https://learn.chatgpt.com/docs/enterprise/plugin-management).

### Codex

```text
codex plugin marketplace add Artypoul/gigma-mcp --ref main
codex plugin add gigma-mcp@gigma-mcp
```

To update an existing installation:

```text
codex plugin marketplace upgrade gigma-mcp
codex plugin add gigma-mcp@gigma-mcp
```

The plugin declares `gigma` in its root `mcp.json`. The client loads that MCP
configuration alongside its skills. Keep one `gigma` registration only; remove
an old manually configured duplicate only if it exists. Start a new conversation
after an update and verify that `erp_dialog_check`, `erp_dialog_start`,
`erp_dialog_status`, `erp_dialog_connect` and `erp_dialog_me` are available.
Adding a marketplace in Codex configures Codex, not a separate ChatGPT account.

Version 0.3.1 removed the unsupported `extensions` field used in version 0.3.0.
The inspected [Codex parser](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
can otherwise omit the MCP server while loading skills. Update an older
installation to the current marketplace version; the native callback flow
remains unchanged.

### Claude Code

```text
claude plugin marketplace add Artypoul/gigma-mcp
claude plugin install gigma-mcp@gigma-mcp
```

### Cursor

Install the `gigma-mcp` entry from the repository marketplace. The entry's source
is `plugins/gigma-mcp`, including its Cursor manifest and MCP configuration.

## Verify installation

From a repository checkout, with Codex installed:

```text
python validate_plugin.py
python check_client_registration.py --marketplace-root .
```

The real client reads the checked-in marketplace catalog and its declared
plugin source. The check requires all six skills and exactly one MCP server,
`gigma`. It does not install the plugin or authenticate an owner.

From either a repository checkout or the installed plugin directory:

```text
python check_live_contract.py
```

This separate read-only check inspects the server's discovery contract without
calling owner tools. It must report a text-only contract. If a client still
shows a choice card, inspect stale or different metadata; do not answer the
same login choice twice.

For a ZIP-only client, `python build_chatgpt_package.py` from a checkout builds
a separate portable package. That artifact does not establish a GitHub
marketplace subscription. The package's `mcp.json` already contains the server
endpoint, so marketplace installation does not require a manual MCP entry.

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
