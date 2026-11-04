---
name: gigma-owner-setup
description: Install and verify the Gigma plugin and its native owner transport.
---

# Gigma owner setup

Use this skill for installation, first-run verification and transport
troubleshooting. The `gigma-owner-auth` skill owns the callback flow; do not
repeat its steps here.

- Install the package from the public marketplace repository.
- Verify the `gigma` server is present in the active client.
- Do not treat installation as owner login or production readiness.
- For this native flow do not run `codex mcp login gigma`.
- If `erp_dialog_*` tools are missing, stop and report the contract mismatch.
- Verify that the active client has exactly one `gigma` registration; remove a
  manually configured duplicate before starting a new chat.
- Route connection, callback state, `erp_dialog_me` and logout to
  `gigma-owner-auth`.

Use [mcp-client-setup](../../../../docs/mcp-client-setup.md) and
[mcp-troubleshooting](../../../../docs/mcp-troubleshooting.md) as the user-facing
source.
