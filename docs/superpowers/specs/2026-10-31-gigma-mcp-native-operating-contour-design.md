# Native Gigma MCP operating contour

## Intent

Make the public Gigma plugin understandable after installation: the user can
connect an owner workspace through the native callback, understand the project
model, choose a safe goal, approve writes, recover from bounded failures, and
disconnect without handling capabilities.

## Scope

This change is limited to the public package repository:

- README and package README;
- user-facing docs and examples;
- native owner skills;
- dependency-free package validation.

The backend is read-only source of truth. No backend, workflow, server setting,
secret, OAuth implementation or ERP API change belongs here.

## Auth boundary

The package uses the native chat callback flow exposed by \`erp_dialog_*\`.
Host-managed OAuth/PKCE is a separate mode for confidential clients and is not
mixed into a native attempt. Installation is not owner login and does not prove
production readiness.

## User model

The plugin explains workspace, application, service client, subscription
catalog, plan, subscription, payment review and investigation in plain
language. It does not present the ERP storefront/order/catalog surface as if it
were owner MCP.

## Safety

Capabilities, callback proofs, tokens, secrets, payment evidence containing
sensitive data, and opaque cursors remain out of human-facing text and logs.
Writes require approval. Unknown outcomes stop automatic retry.

## Done when

- setup and callback flow are understandable without tool knowledge;
- post-connect workspace overview and action menu are documented;
- read/write and confidential HTTP boundaries are explicit;
- errors and multi-message recovery have user-facing actions;
- skills route plain-language goals;
- validator checks docs, manifests, endpoint and secret boundaries;
- public package checks pass and the live MCP read-only contract is recorded.
