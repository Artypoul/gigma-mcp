# Callback state persistence implementation plan

> Spec: `docs/superpowers/specs/2026-10-31-callback-state-persistence-design.md`

## Goal

Make the shared `gigma-owner-auth` skill preserve callback state across chat
messages, prevent parallel callback attempts, and enforce the `status` →
`connect` transition without changing the server contract.

## Files and responsibilities

- `plugins/gigma-mcp/skills/gigma-owner-auth/SKILL.md`: private callback state
  record, single-flight guard, recovery rules, and status/connect transition.
- `validate_plugin.py`: dependency-free contract checks for those rules and
  the no-secret/no-OAuth boundaries.
- `README.md` and `plugins/gigma-mcp/README.md`: user-facing explanation of
  the stateful flow and text fallback.

## Task 1: Add failing contract checks

1. Extend `validate_plugin.py` with required state-record, guard, recovery,
   and ordered `status`/`connect` markers.
2. Run `python validate_plugin.py` and record the expected failure because the
   current skill lacks the new markers.

## Task 2: Implement the skill state protocol

1. Add the private `gigma_owner_callback` record fields and lifecycle rules.
2. Define exact-key retry behavior, one-active-attempt guard, status-first
   recovery, and one deliberate connect.
3. Keep capabilities and idempotency keys out of user-facing copy, logs, and
   URLs; preserve existing terminal and unknown-outcome rules.
4. Run `python validate_plugin.py` and confirm the contract passes.

## Task 3: Document host fallback and verification

1. Add concise state/recovery guidance to both README files.
2. Run validator, Ruff check, and Ruff format check on `validate_plugin.py`.
3. Run the backend focused MCP dialog tests from the existing isolated
   environment to verify the server-side race and `status` → `connect`
   contract remains green.
4. Run `git diff --check` and review the exact diff for secrets, workflows,
   generated files, and unrelated changes.

## Done when

- The validator fails before the skill change and passes afterwards.
- Both README files explain the stateful callback flow and text fallback.
- Backend callback tests covering status/connect and concurrent start/connect
  pass on the current target checkout.
- No server, workflow, secret, or production configuration is changed.
