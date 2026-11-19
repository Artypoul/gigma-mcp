# Native owner MCP troubleshooting

## Version 0.3.0 loads skills but omits the MCP server

Version 0.3.0 included `extensions.com.openai.auth` inside the portable
`mcp.json` server entry. The inspected [Codex portable parser](https://github.com/openai/codex/blob/b9559ff737000a4fcf7a0e12c3353cca1ea4d008/codex-rs/codex-mcp/src/agent_plugin_config.rs)
rejects unknown server fields, so it can skip `gigma` while retaining the skills.
Changing only a legacy compatibility manifest does not fix a client that reads
the root portable configuration.

Update the existing plugin to 0.3.1 and restart the client. That release removes
the unsupported field; the portable server entry contains only the transport
type and URL. The plugin supplies the MCP connection automatically, so no
separate manual registration is needed. Check that the installed client exposes
the `erp_dialog_*` tools. This fixes the parser rejection; host provisioning and
successful owner login still need their own checks. The endpoint and native
callback flow are unchanged.

## Figma is available in ChatGPT, but Gigma is missing

Each plugin has its own installation and connection. A Gigma installation in
Codex does not register it in ChatGPT web. Follow the
[ChatGPT setup guide](chatgpt-setup.md) to install or select the correct cloud
plugin, then inspect its discovered tools. Reuse an existing Gigma connection.
Do not infer a backend outage from an absent tool in the conversation.

If the read-only live probe passes but ChatGPT has no `erp_dialog_*` tools,
inspect the plugin's connection/import diagnostics and selected conversation.
If a direct custom-server connection has stale metadata, use its Refresh action
and select the plugin in a new conversation. A successful package upload alone
does not prove the MCP connection was imported or installed.

## UI and text question both appear

The active client must use one `gigma` registration and one consent path. Remove
any manually configured `gigma` server, close old Gigma chats, restart the
client, and run `python check_live_contract.py` from the installed plugin
directory (alongside `mcp.json`) or the repository checkout root. If the check reports a
text-only contract, a remaining UI card comes from stale or different client
metadata. Do not answer the same login/registration choice twice.

## The plugin installed but no owner session exists

Installation only adds the MCP transport and skills. Start a new chat and write
`Connect me to Gigma`. Do not run host OAuth login for the native attempt.

## Dialog tools are missing

Stop. The active client has not exposed the required native contract. Do not
replace it with REST, `api.gigma.ru`, a guessed alias or a second OAuth flow.
Never execute arbitrary REST or arbitrary SQL from this package. Check the
installed plugin version and the server's `tools/list`.

## Native and OAuth transport instructions disagree

The server permits native dialog discovery without credentials. Select transport
authentication **None** if the host's connection flow asks for it. The portable
MCP configuration does not embed credentials or a per-server auth extension.
The live server may also advertise host-managed OAuth for confidential clients.
Those are separate modes.

If the active host requires OAuth before exposing `erp_dialog_*`, stop and report
a transport contract mismatch. Do not run OAuth and native callback in one
attempt and do not claim that installation fixed the server policy.

## The server is disabled

The server controls owner-MCP and callback flags. A plugin cannot enable them.
A disabled transport may still have unrelated discovery routes. Report the
specific unavailable MCP route and do not claim production readiness.

## The callback is waiting

Keep the same attempt and call from the same phone. Do not start another callback
while the current one is pending. Use bounded status polling with visible
progress. If the user wants to stop, ask before calling cancel.

## `expired` or `cancelled`

Report the terminal state. Finish the old attempt and start a new check with a
new generated idempotency key. Never reuse a stale capability.

## `provider_outcome_unknown`

Stop. Do not auto-reconcile, cancel, restart or issue a second session. Explain
that the provider result is unknown and ask whether the user wants the explicit
supported reconcile action.

## `recovery_required`

Stop and report that the server requires bounded recovery. Never ask the user
to paste a capability. If the connect response was lost, call status first and
allow only the deliberate recovery path supported by the server.

## The host lost state between messages

Do not invent or request a token. If the opaque state is still available, resume
with status. Otherwise let the old dialog terminate and start a fresh check.

## `rate_limited`

Wait for the server's retry boundary. Do not launch parallel callbacks or retry
a write automatically.

## Ambiguous counterparty

If a phone maps to multiple identities, report ambiguity and stop. Never choose
the first match.

## Payment or provider write failed

Report the bounded error without raw provider or database details. Re-read the
safe resource if the contract supports it. Unknown outcomes require an explicit
operator decision, not a blind retry.

## Text flow only

All clients should use the text callback flow. The public package does not
advertise or depend on optional UI card. If a client still renders a card, that
behavior comes from live backend metadata and requires a separate backend change.
The text callback sequence remains the source of truth.

## Transport URL or redirect mismatch

The package's canonical transport endpoint is
`https://api.auth.gigma.ru/mcp/owner/`. The no-slash URL redirects with `307`,
which some POST clients do not follow. Verify the exact POST transport behavior
with a read-only initialize probe and keep the slash route in package config.

## Logout

Write `Отключи меня от Gigma`. The agent revokes the session, discards the
capability and requires a fresh connection for later work.
