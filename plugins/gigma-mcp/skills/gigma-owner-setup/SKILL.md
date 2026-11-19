---
name: gigma-owner-setup
description: Install, connect and troubleshoot Gigma MCP in ChatGPT or local agent clients; use when its tools are missing or setup needs verification.
---

# Gigma owner setup

Use this skill for installation, first-run verification and transport
troubleshooting. The `gigma-owner-auth` skill owns the callback flow; do not
repeat its steps here.

- Identify the active host. For ChatGPT web, use the packaged
  [ChatGPT setup guide](../../docs/chatgpt-setup.md) and the supported cloud
  plugin connection flow. For Codex, Claude Code or Cursor, use the public
  marketplace instructions in the client setup guide.
- Reuse an existing Gigma plugin or connection when available. Verify the
  actual discovered `erp_dialog_*` tools in the active conversation; a skill,
  repository link or plugin card alone does not prove tool access.
- Do not treat installation as owner login or production readiness.
- For ChatGPT web, a registered custom MCP connection provides the tools.
  A GitHub marketplace or standalone MCP archive can be Desktop only. Use
  the guide's web connection route with **No authentication** for transport;
  keep Gigma's existing callback authentication inside `erp_dialog_*`.
  An App-bound package can reference only a verified existing Gigma App ID.
  A package build or invented `.app.json` identifier cannot register a server.
- For a command menu, use [chat commands](../../docs/chat-commands.md) without
  tool calls. Check the actual conversation tool inventory; do not call
  `erp_dialog_check` as a health probe because it can prepare a login attempt.
- For this native flow do not run `codex mcp login gigma`.
- If `erp_dialog_*` tools are missing, report which layer is unverified:
  plugin installation, MCP discovery or conversation tool availability. Do not
  ask for a phone or start owner authentication before the tools are available.
  Do not diagnose a backend outage without a failed live-server check.
- Verify that the active client has exactly one `gigma` registration; remove a
  manually configured duplicate before starting a new chat.
- Route connection, callback state, `erp_dialog_me` and logout to
  `gigma-owner-auth`.

Use [mcp-client-setup](../../docs/mcp-client-setup.md) and
[mcp-troubleshooting](../../docs/mcp-troubleshooting.md) as the user-facing
source.
