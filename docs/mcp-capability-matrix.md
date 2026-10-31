# Owner MCP capability matrix

The executable source of tool schemas is the live `tools/list` response. This
matrix is a user-facing map, not a replacement for the server schemas.

## Session

| Goal | Tool group | Mode | Boundary |
|---|---|---|---|
| Connect owner | `erp_dialog_*` | read/write | Native callback only; capabilities stay in MCP state |
| Show current workspace | `erp_dialog_me` | read | Safe summary only |
| Disconnect | `erp_dialog_logout` | write | Durable session revoke and capability discard |

Legacy `erp_me` and `erp_logout` may remain callable by explicit name while
being omitted from the default catalog. Do not assume their visibility implies
a second login flow.

## Owner operations

| Goal | Tools | Mode | Preconditions |
|---|---|---|---|
| List/read applications | `erp_list_applications`, `erp_get_application` | read | Active owner session |
| Change application state | create/update/activate/deactivate/archive/restore | write | Target app, approval, current schema/ETag |
| Read service clients | list/get/activate/deactivate | read/write | Application scope |
| Read/create counterparty reference | get/find/create | read/write | Application permission; ambiguous identity fails closed |
| Inspect counterparty/activity | investigation and activity tools | read | One valid selector and bounded cursor |

## Subscription operations

| Goal | Tools | Mode | Preconditions |
|---|---|---|---|
| Catalog entries | catalog list/get/create/update/archive | read/write | Workspace scope and ETag for mutation |
| Price revisions | revision list/create/publish | read/write | Entry/plan, immutable revision, current ETag |
| Assign catalog | assignment list/get/create/update/detach | read/write | Application and request ID where required |
| Plans | plan list/get/create/update/archive | read/write | Application and ETag/request ID where required |
| Autopay policy | list/create/publish | read/write | Application policy scope |
| Provider metadata | types/bindings list/get | read | Application scope |
| Provider binding state | create/update/select/deselect/enable/disable/rotate | write | Profile-only input, readiness and current ETag |
| Subscriptions | list/get/cancel/resume/grant-free/status-events | read/write | Application, subject, ETag/request ID |
| Payment review | list/get/reconcile/verify/compensation/close | read/write | Payment case, explicit approval, safe evidence |

Provider binding MCP operations never accept or return raw credentials. Secret
provisioning and rotation remain on the trusted confidential channel even when
the MCP tool accepts a server-side credential profile name.

## Explicitly outside this package

- customer checkout and payment submission;
- manager impersonation or S2S impersonation;
- manual time extension;
- arbitrary HTTP or SQL;
- warehouse, inventory, nomenclature, storefront and order operations;
- miniapp and browser authentication;
- logo uploads and confidential credential delivery.

## Universal safety rules

- Workspace comes from the verified session.
- Canonical application names must belong to that workspace.
- Closed DTOs reject unknown fields and wrong types.
- Foreign and unknown resources have neutral outward behavior.
- Ambiguous phone identity fails closed.
- ETag-protected writes use the current ETag.
- Receipt-bearing writes use the required nonzero request ID.
- Unknown outcomes stop; they do not trigger blind retries.
- Opaque capabilities and cursors never enter chat, logs, URLs, headers or
  another service.
