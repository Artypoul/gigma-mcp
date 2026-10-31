# Native callback buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standard MCP Apps choice card to the owner callback check while preserving the existing text flow in Claude Code and Cursor.

**Architecture:** The backend owner MCP will serve a versioned static HTML resource and attach `_meta.ui.resourceUri` to `erp_dialog_check`. The component will use the MCP Apps `ui/initialize`/`tools/call` bridge to call the existing `erp_dialog_start` tool; the server remains authoritative for consent, capabilities, and validation. The package repository will document capability-based rendering and retain the existing skill fallback.

**Tech Stack:** Python 3.13, FastMCP/mcp 1.30.0, FastAPI, pytest/httpx, vanilla HTML/CSS/JavaScript, Agent Plugins manifests.

**Spec:** `docs/superpowers/specs/2026-10-31-mcp-apps-callback-buttons-design.md`

## Global Constraints

- Keep `erp_dialog_start` as the only operation that starts login or registration.
- Keep `consent: true`, action, project-name, idempotency, and capability validation in the existing strict server DTOs.
- Use MCP Apps `_meta.ui.resourceUri` and `text/html;profile=mcp-app`; do not add a REST endpoint or OAuth path.
- Advertise `io.modelcontextprotocol/ui` with the supported UI MIME type during MCP initialization; keep the mcp 1.30.0 pin.
- Never render, log, persist, or place callback/session capabilities in model-visible UI copy.
- Hosts without MCP Apps UI must keep the current text fallback.
- Do not modify `.github/workflows/`, production configuration, secrets, or server settings.
- Donor code and installed skills remain read-only.

## Review Focus

- **MCP metadata compatibility:** `tools/list` exposes the resource URI only on `erp_dialog_check`; test exact URI and absence of credential values.
- **Resource transport:** `resources/read` returns the exact MCP Apps MIME type and HTML; test unknown resources still fail safely.
- **Consent boundary:** button calls use `consent: true`, preserve the dialog capability, and never call `erp_dialog_start` before a click; test HTML contract and existing server validation.
- **Registration input:** login omits `project_name`, while registration requires a non-empty project name; test both button paths and server DTO behavior.
- **Fallback behavior:** skill and normal tool results remain usable when the host ignores UI metadata; test package docs/skill markers and unchanged dialog tools.

### Task 1: Add failing MCP Apps resource and metadata tests in the backend

**Files:**
- Modify: `D:/GitHub/api.auth.gigma.ru/tests/test_mcp_owner_session.py`
- Modify: `D:/GitHub/api.auth.gigma.ru/tests/test_mcp_owner_dispatch.py`

**Interfaces:**
- Consumes: current `fake_app()`, `StrictOwnerMCP`, and streamable HTTP test helpers.
- Produces: test names and exact assertions for the resource URI, tool `_meta`, MIME type, and fallback tool list.

- [ ] **Step 1: Write the failing tests**

  Add tests that inspect MCP initialization capabilities and call `tools/list`
  without Bearer. Assert the `io.modelcontextprotocol/ui` extension advertises
  `text/html;profile=mcp-app`, and assert `erp_dialog_check`
  has `_meta.ui.resourceUri == "ui://gigma/owner-auth/v1.html"`, while its
  metadata contains no `dialog_capability`, phone, or token value. Add a
  `resources/read` request for that URI and assert one content item with MIME
  type `text/html;profile=mcp-app`, the two action labels, and the bridge
  methods `ui/initialize` and `tools/call`.

- [ ] **Step 2: Run the focused tests and verify they fail**

  Run from the backend checkout:

  ```text
  C:\DEV\api.auth.gigma.ru\.venv\Scripts\python.exe -m pytest -q tests/test_mcp_owner_session.py tests/test_mcp_owner_dispatch.py
  ```

  Expected: FAIL because the current tool has no UI metadata and no registered
  MCP Apps resource.

### Task 2: Implement the owner MCP resource and descriptor metadata

**Files:**
- Create: `D:/GitHub/api.auth.gigma.ru/src/gigma_auth/modules/authentication/presentation/mcp_owner_ui.py`
- Modify: `D:/GitHub/api.auth.gigma.ru/src/gigma_auth/modules/authentication/presentation/mcp_owner.py`
- Test: tests from Task 1

**Interfaces:**
- Consumes: `mcp.server.fastmcp.resources.TextResource`, `MCPTool._meta`, and the existing `register_dialog_tool` path.
- Produces: `OWNER_AUTH_UI_URI`, `OWNER_AUTH_UI_HTML`, `owner_auth_ui_resource()`, and an optional `meta` parameter on `register_dialog_tool`.

- [ ] **Step 1: Implement the static resource module**

  Define `OWNER_AUTH_UI_URI = "ui://gigma/owner-auth/v1.html"`, the exact
  `text/html;profile=mcp-app` MIME type, and a dependency-free HTML component
  with an inline card, accessible buttons, a registration project-name input,
  and bridge code based on JSON-RPC `postMessage`. Keep the dialog capability
  only in JavaScript memory. Show server error text without exposing opaque
  capability values.

- [ ] **Step 2: Extend strict dialog registration**

  Add `meta: dict[str, Any] | None = None` to
  `StrictOwnerMCP.register_dialog_tool` and pass it as `_meta=meta` to `MCPTool`.
  Register a `TextResource` for `OWNER_AUTH_UI_URI` in `build_owner_mcp`, then
  give only `erp_dialog_check` the metadata
  `{ "ui": { "resourceUri": OWNER_AUTH_UI_URI } }`.
  Add a narrow initialization-options adapter on the existing FastMCP 1.30.0
  server so the standard `io.modelcontextprotocol/ui` capability is included.

- [ ] **Step 3: Run the focused tests and verify they pass**

  Run the Task 1 pytest command. Expected: all targeted tests pass, including
  existing callback and capability-boundary tests.

### Task 3: Add package fallback documentation and contract checks

**Files:**
- Modify: `D:/GitHub/gigma-mcp/README.md`
- Modify: `D:/GitHub/gigma-mcp/plugins/gigma-mcp/README.md`
- Modify: `D:/GitHub/gigma-mcp/validate_plugin.py`
- Test: `D:/GitHub/gigma-mcp/validate_plugin.py`

**Interfaces:**
- Consumes: the backend UI URI and the existing `gigma-owner-auth` skill.
- Produces: public documentation that explains capability-based buttons and
  text fallback without changing the skill file.

- [ ] **Step 1: Add the fallback and capability documentation**

  Explain that compatible native chats render the MCP Apps card after
  `erp_dialog_check`; Claude and Cursor continue with the text sequence when
  they do not render UI resources. State that users must not run host OAuth
  login and that the server remains the source of truth.

- [ ] **Step 2: Extend the dependency-free validator**

  Require both README files to mention MCP Apps UI and the text fallback, while
  continuing to require all callback tools, the canonical endpoint, and the
  no-OAuth Codex configuration. Do not validate implementation details that
  belong to the backend repository.

- [ ] **Step 3: Run package validation**

  ```text
  C:\DEV\api.auth.gigma.ru\.venv\Scripts\python.exe validate_plugin.py
  C:\DEV\api.auth.gigma.ru\.venv\Scripts\python.exe -m ruff check validate_plugin.py
  C:\DEV\api.auth.gigma.ru\.venv\Scripts\python.exe -m ruff format --check validate_plugin.py
  ```

  Expected: validation OK, Ruff check passes, and formatting is clean.

### Task 4: Cross-repository verification and PR handoff

**Files:**
- Modify: none beyond Tasks 1–3
- Test: backend focused MCP tests, package validator, live read-only `tools/list`

**Interfaces:**
- Consumes: the exact backend and package PR heads.
- Produces: two reviewable commits/PRs with linked evidence; backend merge is
  required before any production UI claim.

- [ ] **Step 1: Run backend static and focused checks**

  Run the focused MCP tests, Ruff check/format on changed backend files, and
  `git diff --check` on the exact backend head.

- [ ] **Step 2: Run package checks and live read-only probe**

  Run package validation and POST an unauthenticated `tools/list` request to
  `https://api.auth.gigma.ru/mcp/owner/`; verify HTTP 200, dialog tools, and
  the new UI metadata only after the backend change is deployed to the testable
  environment. Before deployment, use the mounted test app as evidence.

- [ ] **Step 3: Review exact diffs and open PRs**

  Confirm no skills, workflows, secrets, or production settings changed. Open
  Ready for review PRs with the design and test evidence; do not merge or
  deploy until the owner explicitly requests those actions.

## Commit Boundaries

- Backend commit: `feat: add MCP Apps callback choice UI`.
- Package commit: `docs: describe MCP Apps callback fallback`.
- Keep the backend and package changes separately reviewable because they live
  in different repositories and have different release paths.
