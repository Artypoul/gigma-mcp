# Gigma MCP

Public distribution repository for the Gigma owner MCP plugin for ChatGPT,
Codex, Claude Code, and Cursor. The package contains client manifests, the native callback
skill, user-facing workflow documentation, and the remote MCP configuration.
Authentication and business logic remain on the Gigma server.

## What this package is

This package connects an agent to the **Gigma owner MCP**:

`https://api.auth.gigma.ru/mcp/owner/`

The native chat flow signs an owner into a Gigma workspace through a callback
call. It then lets the agent work with owner-side applications, subscription
catalogs, subscriptions, payment-review records, counterparties, and activity
evidence.

It is not the whole ERP API. Warehouses, products, storefront content, orders,
miniapps, and browser sessions belong to other Gigma surfaces.

Read [the client setup guide](docs/mcp-client-setup.md) before installation.
Read [the project workflows](docs/gigma-project-workflows.md) to understand
what the agent can do after connection.

## Install

### ChatGPT

Use the [ChatGPT setup guide (Russian)](docs/chatgpt-setup.md). A Codex
marketplace installation does not register the server in ChatGPT web.

The ChatGPT connection uses the existing HTTPS endpoint
`https://api.auth.gigma.ru/mcp/owner/`, Streamable HTTP, and transport
authentication **None**. Owner authentication still happens through the
native callback tools; transport discovery does not grant workspace access.

To build the complete private plugin, including its six workflow skills:

```text
python build_chatgpt_package.py
```

The builder validates the package and writes
`dist/gigma-mcp-<version>-chatgpt.zip`. Install this single-plugin archive
through Plugin Creator. The package declares one `gigma` MCP connection in
`mcp.json`, so a compatible client registers it with the six skills when the
plugin is installed and enabled. Complete any connection steps shown by the
host; no separately added MCP server is needed. Update an existing Gigma plugin
instead of creating a duplicate. The custom-server flow in the ChatGPT guide
is an alternative for using the endpoint without the complete plugin.

Installation and successful discovery must be checked separately. Verify the
actual `erp_dialog_*` tools in the selected ChatGPT conversation before asking
for a phone or beginning owner login.

### Codex, Claude Code and Cursor

Codex:

```text
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

The plugin supplies the `gigma` server configuration automatically; there is no
`codex mcp add` step. Keep exactly one `gigma` registration in the active client.
After removing an old manual entry or updating the plugin, close old Gigma chats
and restart the client. Check the plugin's MCP connection and the available
`erp_dialog_*` tools. Separately verify the deployed text-only contract with:

```text
python check_live_contract.py
```

Claude Code:

```text
claude plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install `gigma-mcp` from the repository marketplace. The package
also includes a manual `mcp.json` for clients that support direct MCP setup.

If `codex mcp list` already contains a manually added server named `gigma`,
remove that old entry before installing the plugin:

```text
codex mcp remove gigma
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

Installation only installs the transport and skills. It does not log the owner
into a workspace and does not prove production availability.

For this package's native chat flow, do **not** run `codex mcp login gigma`.
The server permits discovery of the native dialog tools without credentials.
The portable MCP entry contains the transport type and URL, with no embedded
credentials or per-server authentication extension. Select transport
authentication **None** if the host's connection flow asks for it. The package
uses the slash route
`https://api.auth.gigma.ru/mcp/owner/` to avoid a POST redirect. The live
server may also advertise host-managed OAuth for other confidential transport
clients. If the active host requires OAuth before it exposes `erp_dialog_*`,
stop and report a transport contract mismatch; do not mix OAuth and native
callback in one attempt.

### Updating from 0.3.0

Version 0.3.0 put `extensions.com.openai.auth` inside the portable MCP server
entry. The [Codex portable parser at the inspected commit](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
rejects unknown server fields, so it can skip `gigma` while loading the skills.
Version 0.3.1 removes that unsupported field. This fixes the configuration
rejection in that parser; host installation, tool discovery and owner login
remain separate checks. The endpoint and native callback flow are unchanged.

### Verify automatic registration

With Codex installed, run the repository's read-only client check:

```text
python check_client_registration.py --regression-check
```

It asks the real Codex loader to read a temporary copy of this plugin and checks
for one `gigma` MCP server and all six skills. The regression check also verifies
that the former unsupported field reproduces the missing server. It does not
install the plugin, start an agent turn, call Gigma tools or perform owner login.
CI runs this check against the built ZIP using pinned Codex 0.170.0. Startup or
inspection failures fail the job instead of reporting successful registration.

## Connect Gigma

After installation, open a new agent chat and write:

```text
Connect me to Gigma
```

If a valid session is already available and the server supports checking it,
the agent continues that session without another login or registration choice.
For a new callback connection, the agent will:

1. ask for the owner phone without asking for a token or password;
2. check whether a project exists;
3. show one login or registration choice path;
4. ask for a project name only for text-based registration;
5. show a callback number;
6. wait for a call from the same phone;
7. verify the callback;
8. connect one owner session;
9. show a safe workspace summary and next actions.

The same callback state must survive the messages between starting the call and
checking its status. If the host loses that state, the agent must use the
documented recovery path and never ask you to paste a capability.

All clients use the text callback flow. The public package does not advertise or
depend on an optional UI card. If a client still renders a UI card, that metadata
comes from a stale or different client registration, cached metadata, or the live
backend. Do not answer the same choice twice; restart the client and run the live
contract check before continuing.

## What to ask the agent

After connection, ask for a goal in plain language:

- “Покажи мои приложения и их состояние.”
- “Покажи тарифы и опубликованные версии.”
- “Найди активные подписки.”
- “Проверь платёжные инциденты.”
- “Расследуй контрагента по номеру.”
- “Создай приложение, но сначала покажи план изменений.”

The agent must ask for confirmation before a write and must stop on an unknown
outcome instead of retrying blindly.

## Disconnect

Write:

```text
Отключи меня от Gigma
```

The agent revokes the owner session, discards its opaque capability, and stops
calling business tools.

## Safety and boundaries

- Never paste a token, callback proof, capability, or provider secret into chat.
- Capabilities remain inside MCP tool state and are never placed in URLs, logs,
  files, or browser storage.
- The verified session selects the workspace; user input cannot switch tenants.
- The package does not contain credentials, callback proofs, a local MCP server,
  or backend runtime code.
- ERP operations such as warehouses, nomenclature, storefronts, orders, and
  miniapps are outside this owner MCP package.

See the [capability matrix](docs/mcp-capability-matrix.md), [security guide](docs/mcp-security-and-approvals.md), and [troubleshooting guide](docs/mcp-troubleshooting.md).
