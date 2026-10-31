# Native owner MCP troubleshooting

## The plugin installed but no owner session exists

Installation only adds the MCP transport and skills. Start a new chat and write
\`Connect me to Gigma\`. Do not run host OAuth login for the native attempt.

## Dialog tools are missing

Stop. The active client has not exposed the required native contract. Do not
replace it with REST, \`api.gigma.ru\`, a guessed alias or a second OAuth flow.
Never execute arbitrary REST or arbitrary SQL from this package. Check the
installed plugin version and the server's \`tools/list\`.

## Native and OAuth transport instructions disagree

The package maps Codex to \`auth.type: none\` so native dialog tools can be
discovered without a pasted token. The live server may also advertise
host-managed OAuth for confidential clients. Those are separate modes.

If the active host requires OAuth before exposing \`erp_dialog_*\`, stop and report
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

## \`expired\` or \`cancelled\`

Report the terminal state. Finish the old attempt and start a new check with a
new generated idempotency key. Never reuse a stale capability.

## \`provider_outcome_unknown\`

Stop. Do not auto-reconcile, cancel, restart or issue a second session. Explain
that the provider result is unknown and ask whether the user wants the explicit
supported reconcile action.

## \`recovery_required\`

Stop and report that the server requires bounded recovery. Never ask the user
to paste a capability. If the connect response was lost, call status first and
allow only the deliberate recovery path supported by the server.

## The host lost state between messages

Do not invent or request a token. If the opaque state is still available, resume
with status. Otherwise let the old dialog terminate and start a fresh check.

## \`rate_limited\`

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
\`https://api.auth.gigma.ru/mcp/owner/\`. The no-slash URL redirects with \`307\`,
which some POST clients do not follow. Verify the exact POST transport behavior
with a read-only initialize probe and keep the slash route in package config.

## Logout

Write \`Отключи меня от Gigma\`. The agent revokes the session, discards the
capability and requires a fresh connection for later work.
