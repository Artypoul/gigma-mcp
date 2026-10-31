# Gigma MCP

Public distribution repository for the Gigma owner MCP plugin for Codex, Claude
Code, and Cursor. The package contains client manifests, the native callback
skill, user-facing workflow documentation, and the remote MCP configuration.
Authentication and business logic remain on the Gigma server.

## What this package is

This package connects an agent to the **Gigma owner MCP**:

`https://api.auth.gigma.ru/mcp/owner`

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
remove that old entry before installing the plugin:

```text
codex mcp remove gigma
codex plugin marketplace add https://github.com/Artypoul/gigma-mcp.git
codex plugin add gigma-mcp@gigma-mcp
```

Installation only installs the transport and skills. It does not log the owner
into a workspace and does not prove production availability.

For this package's native chat flow, do **not** run `codex mcp login gigma`.
The package maps Codex to `auth.type: none) so native dialog tools can be
discovered without a pasted token. The live server may also advertise
host-managed OAuth for other confidential transport clients. If the active host
requires OAuth before it exposes `erp_dialog_*`, stop and report a transport
contract mismatch; do not mix OAuth and native callback in one attempt.

## Connect Gigma

After installation, open a new agent chat and write:

```text
Connect me to Gigma
```

The agent will:

1. ask for the owner phone without asking for a token or password;
2. check whether a project exists;
3. ask you to choose login or registration;
4. ask for a project name only for registration;
5. show a callback number;
6. wait for a call from the same phone;
7. verify the callback;
8. connect one owner session;
9. show a safe workspace summary and next actions.

The same callback state must survive the messages between starting the call and
checking its status. If the host loses that state, the agent must use the
documented recovery path and never ask you to paste a capability.

Compatible native chats can render an MCP Apps choice card after
`erp_dialog_check`. Claude Code and Cursor keep the text fallback when their
host does not render MCP Apps UI. Both paths call the same server-side
`erp_dialog_start` contract.

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
