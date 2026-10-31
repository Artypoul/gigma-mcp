# Read-only MCP contract gate

The public package and backend are released separately. This probe verifies only
that the live owner MCP exposes the native contract expected by the package.

## Probe

Use the exact POST transport endpoint:

\`\`\`text
https://api.auth.gigma.ru/mcp/owner/
\`\`\`

Perform only:

1. \`initialize\`;
2. \`notifications/initialized\`;
3. \`tools/list\`;
4. \`resources/list\`;
5. \`resources/read\` for \`ui://gigma/owner-auth/v1.html\`.

Never call a dialog tool, business tool, provider operation, OAuth login or
anything that requires a phone, capability or token.

## Assertions

- HTTP 200 for the supported transport requests;
- owner MCP server identity and protocol response;
- native dialog tools are present;
- \`erp_dialog_check\` points to the expected UI resource;
- resource MIME is \`text/html;profile=mcp-app\`;
- UI bridge contains \`ui/initialize\` and \`tools/call\`;
- metadata and static HTML contain no capability, token or proof values;
- login/register choice labels are present;
- the package's native-flow documentation matches the live contract.

A live pass proves contract reachability only. It does not prove callback delivery,
Redis/PostgreSQL recovery, provider readiness, staging rehearsal, production
flags, or production deployment.

## Redirect and feature flags

The deployed route may normalize a trailing slash. Verify POST behavior with the
transport client; do not use a GET response as evidence for MCP availability.

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
- whether the result is package-ready, live-contract-ready, or production-ready.

Do not place raw response credentials, callback state, phone numbers or provider
payloads in the evidence.
