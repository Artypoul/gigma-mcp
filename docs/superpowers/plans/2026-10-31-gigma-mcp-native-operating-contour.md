# Native Gigma MCP operating contour Implementation Plan

> **For agentic workers:** Use Superpowers task-by-task. The public package is
> the only write target; api.auth.gigma.ru is a read-only contract source.

**Goal:** Make the public Gigma MCP package understandable and safe from
installation through native callback onboarding, owner operations, recovery and
logout.

**Architecture:** Keep the existing remote MCP endpoint, manifests and native
callback contract. Add user-facing docs, goal-oriented skills and a
dependency-free validator. Verify backend behavior through bounded read-only
MCP probes; do not change backend or server configuration.

**Tech Stack:** Markdown, Agent Plugin manifests, dependency-free Python
validation, read-only MCP JSON-RPC probes.

**Spec:** \`docs/superpowers/specs/2026-10-31-gigma-mcp-native-operating-contour-design.md\`

## Global Constraints

- Canonical endpoint: \`https://api.auth.gigma.ru/mcp/owner\`.
- Native callback and host-managed OAuth are separate modes.
- Do not ask users to paste capabilities, tokens, callback proofs or secrets.
- Do not call ERP API routes from this package.
- Writes require explicit user approval.
- Unknown outcomes must stop automatic retry.
- Backend, workflows, secrets, server flags and deploy configuration are out
  of scope for the package implementation.

## Review Focus

- Multi-message callback state survives from start through status/connect, or
  the agent reports a bounded recovery path without asking for a capability.
- Login/register choice is explicit and registration asks for a project name only
  after consent.
- Provider/payment unknown outcomes do not become blind retries.
- ERP requests are routed away from owner MCP without dead-ending the user.
- Documentation does not expose capability, token, provider-secret or
  payment-evidence values.

### Task 1: User-facing setup and journey

**Files:**

- Modify: \`README.md\`
- Modify: \`plugins/gigma-mcp/README.md\`
- Modify: \`plugins/gigma-mcp/skills/gigma-owner-auth/SKILL.md\`
- Create: \`docs/mcp-client-setup.md\`
- Create: \`docs/gigma-user-journey.md\`

**Verification:**

\`\`\`text
python validate_plugin.py
python -m compileall -q validate_plugin.py
git diff --check
\`\`\`

### Task 2: Project workflows and capability boundaries

**Files:**

- Create: \`docs/gigma-project-workflows.md\`
- Create: \`docs/mcp-capability-matrix.md\`
- Create: \`docs/mcp-security-and-approvals.md\`
- Create: \`docs/mcp-troubleshooting.md\`
- Create: \`docs/examples/golden-dialogues.md\`

**Verification:**

- every linked document exists;
- every workflow names a safe result and a bounded failure;
- ERP API, confidential HTTP and unsupported operations are explicit;
- payment evidence guidance prohibits secrets and unnecessary personal data.

### Task 3: Goal-oriented skills

**Files:**

- Create: \`plugins/gigma-mcp/skills/gigma-owner-setup/SKILL.md\`
- Create: \`plugins/gigma-mcp/skills/gigma-owner-router/SKILL.md\`
- Create: \`plugins/gigma-mcp/skills/gigma-owner-project-ops/SKILL.md\`
- Create: \`plugins/gigma-mcp/skills/gigma-owner-subscriptions/SKILL.md\`
- Create: \`plugins/gigma-mcp/skills/gigma-owner-investigation/SKILL.md\`

**Verification:**

- each skill has a distinct trigger;
- skills reference discovered schemas;
- no skill contains credential values;
- router routes ERP requests away from this package;
- write skills require approval and prevent blind retries.

### Task 4: Dependency-free package contract validation

**Files:**

- Modify: \`validate_plugin.py\`

**Verification:**

\`\`\`text
python validate_plugin.py
python -m compileall -q validate_plugin.py
git diff --check
\`\`\`

The validator must check required docs/skills, canonical endpoint, native
\`auth.type: none\`, callback markers, text fallback and absence of raw secret
values. It must allow documentation words such as \`OAuth\`,
\`dialog_capability\` and \`session_capability\`.

A negative check mutates a temporary copy, removes a required marker and inserts
a fake secret assignment. The real checkout is not mutated.

### Task 5: Read-only live contract gate

**Files:**

- Create: \`docs/mcp-contract-sync.md\`

Probe only \`initialize\`, \`notifications/initialized\`, \`tools/list\`,
\`resources/list\` and \`resources/read\` for the owner-auth UI resource.

Verify HTTP 200, dialog tool presence, UI URI/MIME, no credential values in
metadata/static HTML, and native documentation consistency. Never call a dialog
or business write tool.

The live gate must record the exact endpoint path and any POST redirect behavior.
It must not claim production readiness, callback delivery or provider readiness.

### Task 6: Cross-client and release handoff

Verify Codex, Claude Code and Cursor installation smoke paths separately.
Confirm the package source, plugin version and canonical endpoint. Keep
backend/live evidence separate from package evidence.

A package release is not an owner-MCP production rollout. Server flags, staging
rehearsal, exact artifact/HEAD, rollback criteria and owner deploy approval
remain separate operational gates.

## Commit boundaries

- \`docs: explain native Gigma MCP user flow\`
- \`feat: make native owner auth user-facing and recoverable\`
- \`docs: add owner MCP workflow and boundaries\`
- \`feat: add owner MCP goal skills\`
- \`test: extend public plugin contract validator\`
- \`docs: add live contract synchronization gate\`

## DoneWhen

- setup, callback, workspace overview, operations, recovery and logout are
  understandable from public docs;
- plain-language requests route to the correct skill;
- public validator and formatting checks pass;
- live read-only contract evidence is recorded;
- no backend, workflow, secret or ERP API changes are present.
