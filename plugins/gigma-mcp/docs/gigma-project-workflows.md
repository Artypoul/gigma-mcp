# Gigma owner workflows

The owner MCP is a control plane for a verified workspace. It is not the whole
ERP API.

## Plain-language model

| User-facing term | MCP meaning |
|---|---|
| Project | owner workspace, the tenant boundary |
| Application | a site, product or client application inside the workspace |
| Service client | confidential backend integration metadata |
| Catalog | subscription catalog entries and assignments |
| Tariff | subscription plan and published price revision |
| Subscription | a customer's access and lifecycle |
| Payment incident | payment-review case requiring operator handling |
| Investigation | redacted counterparty and activity evidence |

The verified callback session chooses the workspace. User input cannot switch
tenants.

## First action after connection

After `erp_dialog_connect`, call `erp_dialog_me`. Then show a safe summary and
offer the next action. Do not start writes automatically.

## Workflow format

Every operation follows:

1. identify the user's goal;
2. perform read-only discovery;
3. state the target application and intended change;
4. ask for confirmation before a write;
5. use the discovered schema, current ETag and required request ID;
6. report the result or the bounded error;
7. never retry an unknown one-time operation blindly.

## Applications

Typical requests:

- “Покажи приложения.”
- “Создай приложение.”
- “Отключи приложение.”
- “Восстанови приложение.”

Use the application list/get tools before a mutation. Archived and disabled
applications must be explained as states, not silently treated as missing.

Credentials and secret issuance remain confidential operations. The agent may
show safe metadata such as client ID presence, but never a secret or secret
reference.

## Catalog, plans and subscriptions

For a new subscription offering:

1. inspect catalog entries and application assignments;
2. inspect or create the plan;
3. create an immutable price revision;
4. publish the revision with the current ETag;
5. verify the published result;
6. only then offer subscription operations.

For a subscription change:

1. identify the application and subscription;
2. read the current state and ETag;
3. explain cancellation, resume or FREE-grant effect;
4. ask for confirmation;
5. call the exact operation once;
6. read back the safe result and status event.

Payment provider bindings exposed by MCP are profile/metadata operations. The
actual server-side credential material must already be provisioned through the
confidential channel; it is never typed into chat.

## Payment review

A payment-review action is an operator mutation. Before sending evidence, tell
the user not to include passwords, tokens, card data, provider payloads or
unnecessary personal data. Do not echo evidence in the response or logs.

Unknown payment/provider results stop the workflow. The agent may offer the
specific supported reconcile or verification action, but never invent a retry.

## Investigation

Investigation accepts the selector supported by the discovered schema. If a
phone maps to multiple candidates, report ambiguity and stop; never select
`matches[0]`.

Responses are redacted projections. They can include structured activity,
authentication, subscription and payment metadata, but not OTP, credentials,
tokens, callback proofs, raw provider payloads or free-text evidence.

Pagination uses the returned opaque page token. Do not modify a continuation's
bound filters or page size.

## ERP boundary

These requests are outside this owner MCP package:

- branches and warehouses;
- nomenclature and inventory;
- storefront pages, menus and content;
- customer checkout and orders;
- miniapp auth;
- browser session integration.

Explain the boundary and route the user to the appropriate ERP API or
server-side SDK workflow. Do not call `api.gigma.ru` from this plugin and do
not invent REST aliases.

## Disconnect

When the user asks to disconnect:

1. call `erp_dialog_logout`;
2. discard the session capability;
3. stop business calls;
4. tell the user that a new connection is required for later work.
