# Owner MCP security and approvals

## Secrets

Never ask the user to paste or read back:

- dialog or session capabilities;
- callback proofs;
- OTPs;
- access or refresh tokens;
- client or provider secrets;
- private keys;
- raw provider payloads.

The agent may show a callback phone number and safe projections returned by the
server. Capabilities and page cursors stay in MCP/tool state.

## Workspace boundary

The server derives the workspace from the verified owner session. Never accept
a workspace ID as a user-controlled switch. Application resource names must
match the verified workspace.

## Read versus write

Reads can run after the owner session is connected. Writes require the normal
approval prompt and a plain-language preview:

- target workspace/application;
- intended state change;
- important irreversible or billing effect;
- identifiers such as plan or subscription;
- whether the operation is replay-safe.

The agent must read the current resource before an ETag-protected update.

## Payment-review evidence

Evidence is operator input, not a place to store credentials. The user must be
told not to include secrets, card data, OTP, tokens, provider payloads or
unnecessary personal data. The agent must not echo evidence or place it in
diagnostic output.

## Unknown outcomes

For `provider_outcome_unknown`, `recovery_required`, or
`unknown_outcome`:

1. stop automatic retries;
2. report that the result is bounded but not confirmed;
3. offer only the explicit reconcile or verification action supported by the
   discovered schema;
4. require a new user decision before cancellation, restart or another write.

## Logout

After `erp_dialog_logout`, discard the capability and stop business calls.
A later operation requires a new owner connection.

## Production boundary

Installing this package does not enable the server. The owner MCP is controlled
by server-side flags, HTTPS/proxy policy, callback delivery, signing keys,
Redis/PostgreSQL state and provider readiness. Production enablement, rollback
and deploy are separate operational actions.
