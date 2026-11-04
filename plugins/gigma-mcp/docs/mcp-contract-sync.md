# Read-only MCP contract gate

The public package and backend are released separately. This probe verifies only
that the live owner MCP exposes the native text callback contract expected by
the package.

## Probe

Use the exact POST transport endpoint:

```text
https://api.auth.gigma.ru/mcp/owner/
```

Run the checker from the repository checkout root or from the installed plugin
directory, alongside `README.md` and `mcp.json`. Both contain the same standalone,
dependency-free script:

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
- exact owner MCP server name, nonempty reported version and the requested
  `2025-06-18` protocol (other negotiated protocols require package review);
- all eight native dialog tools are present, including cancel and reconcile;
- their closed input schemas retain the reviewed field types, required fields,
  capability patterns and bounds, without an added required token;
- at least one business tool is present, and every advertised business tool
  requires the bounded native `session_capability`;
- native and business schemas reject unreviewed root composition/constraints
  that could add hidden credential requirements;
- the text-only contract does not expose UI capability, `resourceUri` or an
  MCP Apps resource;
- `erp_dialog_check` is annotated as stateful but non-destructive, idempotent and
  closed-world (`readOnlyHint=false`, `destructiveHint=false`,
  `openWorldHint=false`);
- catalog pages are complete; duplicate tools, malformed schemas or an unread
  `nextCursor` fail the check.

Native field comparisons deliberately ignore titles/descriptions and permit
new optional fields, but reject unreviewed validation constraints. This is a
conservative package compatibility check, not a general JSON Schema validator.
Additional protected business tools are allowed. The reported version is
recorded, not pinned to the MCP SDK version or treated as a deployment SHA.

The package supports exactly one textual choice after `erp_dialog_check`.
If this text-only check finds UI metadata, the active client
is using a different backend revision, stale metadata or another registration;
stop and clean up the client before continuing.

A live pass proves unauthenticated discovery reachability and the advertised
input contracts only. No dialog or business tool is called, so it does not
prove callable business success, authorization enforcement, callback delivery,
Redis/PostgreSQL recovery, provider readiness, staging rehearsal, production
flags or the identity of the deployed application commit.

The regression fixture in `tests/fixtures/owner_mcp_contract.json` was generated
from the actual backend tool definitions named in its provenance. Tests do not
require a backend checkout, credentials or optional dependencies.

## Installed documentation

Canonical guides are edited in repository `docs/`; the probe source is root
`check_live_contract.py`. Run `python sync_plugin_docs.py` to copy both
byte-for-byte into installed `plugins/gigma-mcp/docs/` and
`plugins/gigma-mcp/check_live_contract.py`. Internal Superpowers documents are excluded.
`python validate_plugin.py` rejects stale copies and resolves local Markdown
links within the installed subtree; `python -m unittest discover -s tests -v`
also checks an isolated copy without repository parents, imports its probe
against the contract fixture and executes its `--help` CLI without network calls.

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
