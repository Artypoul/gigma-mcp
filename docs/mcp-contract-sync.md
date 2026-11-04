# Read-only MCP contract gate

The public package and backend are released separately. This probe verifies only
that the live owner MCP exposes the native text callback contract expected by
the package.

## Probe

Use the exact POST transport endpoint:

```text
https://api.auth.gigma.ru/mcp/owner/
```

Run the repository checker:

```text
python check_live_contract.py
```

The checker performs only:

1. `initialize`;
2. `notifications/initialized`;
3. `tools/list`;
4. `resources/list`.

Never call a dialog tool, business tool, provider operation, OAuth login or
anything that requires a phone, capability or token.

## Assertions

- HTTP 200 for the supported transport requests;
- owner MCP server identity and protocol response;
- native dialog tools are present;
- text callback tools remain callable without a pasted token;
- the text-only contract does not expose UI capability, `resourceUri` or an
  MCP Apps resource;
- `erp_dialog_check` is annotated as stateful but non-destructive, idempotent and
  closed-world (`readOnlyHint=false`, `destructiveHint=false`,
  `openWorldHint=false`);
- the package's native-flow documentation matches the live contract.

The package supports exactly one choice path after `erp_dialog_check`: a
rendered UI card owns consent, or the agent uses the text fallback. It must
never present both. If this text-only check finds UI metadata, the active client
is using a different backend revision, stale metadata or another registration;
stop and clean up the client before continuing.

A live pass proves contract reachability only. It does not prove callback delivery,
Redis/PostgreSQL recovery, provider readiness, staging rehearsal, production
flags or production deployment.

## Redirect and feature flags

The package uses the slash route because the no-slash URL redirects with `307`,
which some POST clients do not follow. Verify POST behavior with the transport
client; do not use a GET response as evidence for MCP availability.

The owner MCP can be disabled by server-side flags. Discovery or unrelated
routes may still respond while the owner transport is unavailable. Report the
specific route and do not claim that plugin installation enables the server.

## Evidence

Record:

- exact public package commit;
- exact backend/live server identity;
- probe timestamp;
- request classes executed;
- assertions passed or failed;
- whether the result is package-ready, live-contract-ready or production-ready.

Do not place raw response credentials, callback state, phone numbers or provider
payloads in the evidence.
