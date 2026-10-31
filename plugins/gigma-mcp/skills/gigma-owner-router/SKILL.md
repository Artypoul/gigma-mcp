---
name: gigma-owner-router
description: Route plain-language Gigma owner goals to the correct MCP workflow.
---

# Gigma owner router

Route by the user's goal, not by an internal tool name.

- connect or register → `gigma-owner-setup` + `gigma-owner-auth`;
- show project or applications → `gigma-owner-project-ops`;
- create or change an application → `gigma-owner-project-ops`;
- create tariffs, catalog entries or subscriptions → `gigma-owner-subscriptions`;
- inspect payment incidents → `gigma-owner-subscriptions`;
- investigate a counterparty or activity → `gigma-owner-investigation`;
- disconnect → `erp_dialog_logout`.

Before business tools, verify that an owner session exists and read the safe
workspace summary. Before a write, describe the target and ask for approval.

Route warehouses, nomenclature, storefronts, orders, miniapps and browser
integration away from this package. Do not call arbitrary REST or SQL and do not
invent `api.gigma.ru` aliases.
