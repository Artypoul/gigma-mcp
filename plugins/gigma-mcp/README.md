# Gigma MCP agent plugin

This package connects ChatGPT, Codex, Claude Code, and Cursor to the existing Gigma owner
MCP at `https://api.auth.gigma.ru/mcp/owner/`. It packages the remote
Streamable HTTP server configuration and skills for the native callback flow
and owner operations. Authentication and business logic remain on the Gigma
server.

## Команды из чата

Выберите подключённый Gigma MCP через `@` и напишите **«Гигма, команды»**.
Агент покажет меню без входа. С действующей сессией можно написать:

- **Гигма, мой проект** → `erp_dialog_me`;
- **Гигма, приложения** → `erp_list_applications`;
- **Гигма, тарифы приложения …** → `erp_subscription_plans_list`;
- **Гигма, все активные подписки** → `erp_workspace_subscriptions_list`;
- **Гигма, платёжные инциденты приложения …** → `erp_payment_review_cases_list`.

[Полный каталог команд](docs/chat-commands.md) содержит 77 имён, назначение
и режим каждой операции. Это обычные фразы, а не специальные slash-команды.
Выполнение возможно, когда инструменты действительно доступны в разговоре.

## Install from the marketplace

- Repository: **https://github.com/Artypoul/gigma-mcp**
- Marketplace: **`gigma-mcp`**
- Plugin selector: **`gigma-mcp@gigma-mcp`**

### ChatGPT

For tools in ChatGPT web, use the
[custom MCP connection route](docs/chatgpt-setup.md#команды-в-веб-чате-chatgpt)
with transport authentication **No authentication**. Owner authentication
continues through the native callback. A private App-bound package can attach
these skills to a verified existing Gigma App; its `.app.json` references that
connection rather than declaring a second server. Building that archive does
not create or authenticate the connection.

In a workspace with marketplace imports enabled, an admin uses **Admin →
Plugins → Add → Import marketplace**, enters the repository URL and leaves
Path empty. Review the **Gigma MCP** import result. For an existing import, use
**Marketplaces → Gigma marketplace → Sync now**.
Read [the ChatGPT guide](docs/chatgpt-setup.md) for permissions and exact fields;
personal-account availability can differ.

Imported plugins with MCP declarations can be marked **Desktop only**, even
when their server is HTTPS. Check the plugin's availability in the intended
client; a loaded skill does not confirm that web MCP tools are available.
See [OpenAI's plugin management documentation](https://learn.chatgpt.com/docs/enterprise/plugin-management).
A ZIP import is a separate package snapshot and does not configure GitHub updates.

### Codex

```text
codex plugin marketplace add Artypoul/gigma-mcp --ref main
codex plugin add gigma-mcp@gigma-mcp
```

For an existing installation:

```text
codex plugin marketplace upgrade gigma-mcp
codex plugin add gigma-mcp@gigma-mcp
```

The plugin supplies the MCP configuration automatically. Keep exactly one `gigma` registration in the active client. Remove an old manual duplicate only
if it exists. After an update, open a new conversation and check for the
`erp_dialog_*` tools.

### Claude Code and Cursor

```text
claude plugin marketplace add Artypoul/gigma-mcp
claude plugin install gigma-mcp@gigma-mcp
```

Cursor can install the `gigma-mcp` entry from the repository marketplace.
For the complete first-run procedure, read
[docs/mcp-client-setup.md](docs/mcp-client-setup.md).

### Check the connection

Run `python check_live_contract.py` from this installed plugin directory,
which includes the bundled [checker](check_live_contract.py).
It checks endpoint discovery without sending a phone number or starting login.
From a full repository checkout, also run:

```text
python check_client_registration.py --marketplace-root .
```

This verifies the actual marketplace with the real Codex loader. The repository
script is not part of this installed package.

Version 0.3.1 removed the unsupported `extensions` field from the portable
server entry after it caused the
[Codex portable parser](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
to omit the MCP server while loading skills. Update older installations to the
current marketplace version. Host tool availability and the owner's callback
login still require their own checks.

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
