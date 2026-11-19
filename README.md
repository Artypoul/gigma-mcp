# Gigma MCP marketplace

Public distribution repository for the Gigma owner MCP plugin for ChatGPT,
Codex, Claude Code, and Cursor. The package contains client manifests, the native callback
skill, user-facing workflow documentation, and the remote MCP configuration.
Authentication and business logic remain on the Gigma server.

## Команды из чата

После подключения сервера выберите Gigma MCP через `@` и напишите:

| Сообщение | Реальный инструмент |
| --- | --- |
| **Гигма, команды** | Меню и проверка доступности инструментов, без входа |
| **Гигма, мой проект** | `erp_dialog_me` |
| **Гигма, приложения** | `erp_list_applications` |
| **Гигма, тарифы приложения …** | `erp_subscription_plans_list` |
| **Гигма, все активные подписки** | `erp_workspace_subscriptions_list` |
| **Гигма, платёжные инциденты приложения …** | `erp_payment_review_cases_list` |
| **Гигма, отключись** | `erp_dialog_logout` |

[Полный каталог: 77 инструментов и готовые фразы](docs/chat-commands.md).
Бизнес-команды используют подтверждённую сессию владельца. Вход остаётся
через существующий callback Gigma.

**Для веб-чата сначала нужен зарегистрированный MCP-сервер в ChatGPT.**
Адрес в GitHub и загруженные навыки сами по себе не предоставляют инструменты.
Используйте [точные поля подключения](docs/chatgpt-setup.md#команды-в-веб-чате-chatgpt):
`https://api.auth.gigma.ru/mcp/owner/`, Streamable HTTP, **No authentication**
на уровне транспорта. Callback выполняется внутри команд `erp_dialog_*`.

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

## Install from the GitHub marketplace

- Repository: **https://github.com/Artypoul/gigma-mcp**
- Marketplace: **`gigma-mcp`**
- Plugin selector: **`gigma-mcp@gigma-mcp`**

The repository publishes one plugin from `plugins/gigma-mcp`. Its marketplace
entries include the six workflow skills and the existing `gigma` MCP connection.
Use the repository URL when adding a marketplace; the server URL is already
in the plugin configuration.

| Client | Marketplace catalog in this repository |
| --- | --- |
| ChatGPT GitHub import / Codex | `.agents/plugins/marketplace.json` |
| Claude Code | `.claude-plugin/marketplace.json` |
| Cursor | `.cursor-plugin/marketplace.json` |

### ChatGPT

For callable tools in ChatGPT web, follow the
[custom MCP connection route](docs/chatgpt-setup.md#команды-в-веб-чате-chatgpt).
The marketplace route below distributes the repository package; verify the
host's tool availability separately.

In a workspace with marketplace imports enabled, an admin opens **Admin →
Plugins → Add → Import marketplace** and enters
`https://github.com/Artypoul/gigma-mcp`. Leave Path empty and use the default
branch or `main`. Review the **Gigma MCP** import result, then configure its
installation policy. The [ChatGPT setup guide (Russian)](docs/chatgpt-setup.md)
describes this workspace-admin flow and **Sync now** updates. Availability in
personal accounts can differ. A ZIP import is a separate snapshot.

ChatGPT can mark imported plugins that declare MCP servers **Desktop only**,
including plugins whose MCP URL uses HTTPS. Check the imported plugin's
availability in the intended client. The repository declares the connection;
web tool availability is controlled by ChatGPT's import/runtime support.
See [OpenAI's plugin management documentation](https://learn.chatgpt.com/docs/enterprise/plugin-management).

### Codex

```text
codex plugin marketplace add Artypoul/gigma-mcp --ref main
codex plugin add gigma-mcp@gigma-mcp
```

To refresh an existing Git marketplace and install its current plugin version:

```text
codex plugin marketplace upgrade gigma-mcp
codex plugin add gigma-mcp@gigma-mcp
```

The plugin supplies the `gigma` server configuration automatically. Keep
exactly one `gigma` registration in the active client. If an old manually added
`gigma` entry is confirmed, remove that duplicate before enabling the plugin.
After an update, start a new conversation and verify that `erp_dialog_*` tools
are available. Adding the repository to Codex configures Codex; ChatGPT has its
own import and installation.

### Claude Code and Cursor

Claude Code:

```text
claude plugin marketplace add Artypoul/gigma-mcp
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install the `gigma-mcp` entry from this repository's marketplace.
Read [the client setup guide](docs/mcp-client-setup.md) for the connection check.

### Verify the repository marketplace

From a repository checkout, with Codex installed:

```text
python validate_plugin.py
python check_client_registration.py --marketplace-root .
```

The second command reads the actual checked-in marketplace catalog through the
real Codex loader. It stages the catalog unchanged with its declared plugin
source, then verifies one `gigma` MCP server and all six skills. It rejects
missing or invalid source paths and component-loading errors. It does not
install the plugin, start an agent turn, call Gigma tools or perform owner login.

The CI workflow checks the repository marketplace and the separately built
portable ZIP with pinned Codex 0.170.0. A separate disposable CI job clones the
published GitHub commit through `codex plugin marketplace add`, installs
`gigma-mcp@gigma-mcp`, and verifies the installed version, enabled state, source,
MCP declaration and six skills with the real client. This installation probe
refuses to run against an existing Codex configuration or outside GitHub CI.
A loader startup failure fails the check; it does not count as successful
registration. Live endpoint discovery is a separate, read-only check:

```text
python check_live_contract.py
```

### Optional portable ZIP

For a client that imports a single-plugin archive:

```text
python build_chatgpt_package.py
```

This writes `dist/gigma-mcp-<version>-chatgpt.zip`. It contains the plugin, its
six skills and its MCP declaration. It does not contain the repository's
marketplace catalogs or establish GitHub updates. Use the marketplace route
above when installing from this repository.

For a **private** package that references an already registered Gigma App,
set `GIGMA_CHATGPT_APP_ID` to its verified App ID and run:

```text
python build_chatgpt_package.py --chatgpt-app-id "$GIGMA_CHATGPT_APP_ID"
```

This writes `dist/gigma-mcp-<version>-chatgpt-app.zip` with a required
`.app.json` reference and the same six skills, without a second MCP declaration.
It does not register the server, grant access, install the package or perform
owner login. The builder checks ID syntax only. See
[App binding and the GitHub reference](docs/chatgpt-setup.md#привязка-пакета-к-приложению-как-у-github)
before using this variant. The default portable archive and marketplace
configuration remain unchanged.

### Transport and existing installations

The native callback transport uses Streamable HTTP at
`https://api.auth.gigma.ru/mcp/owner/`. Select transport authentication **None**
if the host asks; discovery does not grant access to a workspace. Do not run
`codex mcp login gigma` for this native flow. Host-managed OAuth is a separate
mode, and a host demanding OAuth before exposing `erp_dialog_*` must be
reported as a transport mismatch.

Version 0.3.0 put `extensions.com.openai.auth` inside the portable MCP server
entry. The [Codex portable parser at the inspected commit](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
rejects that field and can omit the server while still loading skills.
Version 0.3.1 removed it. Update older installations to the current marketplace
version; keep the server entry limited to the supported transport and URL.
The endpoint and native callback flow are unchanged.

## Connect Gigma

After installation and verification that `erp_dialog_*` tools are exposed,
open a new agent chat and write:

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
