---
name: gigma-owner-setup
description: Install and verify the Gigma plugin, then start native owner onboarding.
---

# Gigma owner setup

Use this skill for installation, first-run verification, native callback onboarding
and transport troubleshooting.

- Install the package from the public marketplace repository.
- Verify the \`gigma\` server is present in the active client.
- Do not treat installation as owner login or production readiness.
- For this native flow do not run \`codex mcp login gigma\`.
- If \`erp_dialog_*\` tools are missing, stop and report the contract mismatch.
- Ask for the phone, never for a token or callback proof.
- Keep dialog state across messages without putting capabilities in chat.
- After connect, call \`erp_dialog_me\` and offer the project menu.
- On logout, discard the session capability.

Use [mcp-client-setup](../../../docs/mcp-client-setup.md) and
[mcp-troubleshooting](../../../docs/mcp-troubleshooting.md) as the user-facing
source.
