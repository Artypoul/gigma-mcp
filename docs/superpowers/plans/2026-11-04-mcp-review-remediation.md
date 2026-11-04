# MCP review remediation

Goal: close the eight findings from the 2026-11-04 review in both repositories,
verify them on the local Windows test environment, publish reviewed changes,
and complete the authorized deployment through the existing release procedure.

Source of requirements: the eight-item review in this chat and the owner's
instruction to fix every finding, use `D:\Development\gigma-auth`, install any
missing dependencies, and record the test location in both project runbooks.

Constraints: preserve native text callback, no pasted credentials, tenant from
verified claims, existing HTTP compatibility, explicit uncertain-outcome recovery.
No production flags, secrets, workflows, server configuration, or unrelated data
are changed. Local test services listen on loopback and use disposable test data.

## Task 1: Authentication and recovery

- [x] Add failing regressions for OAuth start/deny/status/code races and serialize
  transitions of the same authorization with one existing lock mechanism.
- [x] Reuse the existing owner callback SQL row and encrypted recovery marker to
  persist one native session issuance atomically. Redis projection replay returns
  the same token and original expiry; rollback cannot publish a successful result.
- [x] Report a connected session's lifetime independently of callback expiry.
- [x] Verify unit regressions and actual PostgreSQL failure/concurrency cases.

- [x] Remove OAuth application storage imports and inject router dependencies
  from composition without changing ingress order; all 12 import contracts pass.

## Task 2: Owner business tools

- [x] Reproduce and fix JSON serialization of nonempty investigation timestamps.
- [x] Add paginated, tenant-bound standalone plan revision list/get using the
  existing subscription service and repository, including lost-response recovery.
- [x] Publish accurate external-provider annotations per tool.
- [x] Verify strict inputs, permissions, tenant/parent isolation and SQL execution.

## Task 3: Distribution and compatibility

- [x] Validate all eight native dialog tools and their compatible input schemas;
  reject broken credentials/session-capability contracts with negative fixtures.
- [x] Bundle documentation with the installed plugin and validate packed links.
- [x] Publish a consistent patch version and update release documentation.

## Task 4: Verification and delivery

- [ ] Restore the reusable Python/PostgreSQL/Redis/MinIO test environment under
  `D:\Development\gigma-auth`; preserve existing development data and secrets.
- [ ] Document commands, isolation boundaries and results in both runbooks.
- [ ] Run focused regressions, PostgreSQL suites, applicable full-suite checks,
  Ruff, type/import checks, AIP evidence and current-diff independent review.
- [ ] Publish code PRs, inspect exact-head required checks and review comments.
- [ ] Follow owner-only merge and existing manual production deployment rules;
  verify deployed revision, health and public MCP contract before completion.

Review focus: post-commit Redis loss, terminal cancellation, expired callbacks
with valid sessions, foreign resource references, nonempty/possible event rows,
missing required tools, new credentials in schemas, and installed-package paths.
