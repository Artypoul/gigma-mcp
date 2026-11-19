---
name: gigma-owner-router
description: Handle Gigma command/menu requests and route concrete chat requests for applications, tariffs, subscriptions, payments, counterparties, connection or logout to the owner MCP workflow.
---

# Gigma owner router

Route by the user's goal, not by an internal tool name.

For “Гигма, команды”, “Гигма, помощь” or a request for callable commands,
read the packaged [command catalog](../../docs/chat-commands.md). Show a short
menu with the exact matching tool names. Distinguish tools actually exposed
in the active conversation from the server catalog documented there. Do not
call tools, request a phone or start callback authentication just to show help.

Treat the catalog's phrases as ordinary chat requests, not installed slash
commands. For example, “Гигма, приложения” routes to `erp_list_applications`;
“Гигма, тарифы приложения …” routes to `erp_subscription_plans_list`; and
“Гигма, все активные подписки” routes to `erp_workspace_subscriptions_list`
with a state filter supported by the live schema. Resolve missing or ambiguous
public identifiers through the owning workflow. Never invent a callable host
function from a documented name or ask the user to supply a capability.

Before execution, check that the needed tools are exposed by the active host.
If only skills are present, use `gigma-owner-setup` and report the connection
gap; owner login cannot make absent tools appear.

- install, verify or troubleshoot transport → `gigma-owner-setup`;
- connect or register → `gigma-owner-auth`;
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
