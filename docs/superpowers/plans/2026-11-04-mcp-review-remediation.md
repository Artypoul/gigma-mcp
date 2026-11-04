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
- [ ] Publish a consistent patch version and update release documentation.

## Task 4: Verification and delivery

- [x] Restore the reusable Python/PostgreSQL/Redis/MinIO test environment under
  `D:\Development\gigma-auth`; preserve existing development data and secrets.
- [x] Document commands, isolation boundaries and results in both runbooks.
- [x] Run focused regressions, PostgreSQL suites, applicable full-suite checks,
  Ruff, type/import checks, AIP evidence and current-diff independent review.
- [x] Publish code PRs, inspect exact-head required checks and review comments.
- [ ] Follow owner-only merge and existing manual production deployment rules;
  verify deployed revision, health and public MCP contract before completion.

Review focus: post-commit Redis loss, terminal cancellation, expired callbacks
with valid sessions, foreign resource references, nonempty/possible event rows,
missing required tools, new credentials in schemas, and installed-package paths.

## Verified delivery evidence

- Backend PR: https://github.com/Artypoul/api.auth.gigma.ru/pull/155 at
  `46bbd5d4f08f241dd6d8a15e298747620db23252`. Required `CI Ruff / ruff` and
  `CI Startup / startup` both succeeded on this exact head.
- Package PR: https://github.com/Artypoul/gigma-mcp/pull/7. Its implementation
  and environment documentation were verified at
  `a3cefdbf1981df52d2b2eaa31d72f2ba0e5d52ef`; this repository has no CI checks.
- Complete backend run: **4199 passed, 126 skipped, 0 failures, 0 errors**,
  exit 0, 859.40 seconds. Source was the exact backend PR head above. JUnit:
  `D:\Development\gigma-auth\review\logs\pytest-20a7564604.xml`, SHA-256
  `472b4da94e62e21f0fa893fa5da6c8708028877a681b2f53b0357c30d033736c`.
  Two skips explicitly reflect Windows symlink privilege WinError 1314; the
  remaining 124 were existing suite skips. The first broad run's failures and
  setup errors were corrected before this successful full run.
- Package: 26 tests passed; bundle synchronization, installed-subtree validation,
  Ruff and metadata-only live probe passed. Public server currently exposes 74
  tools; the reviewed backend adds two plan revision read tools.
- Backend: strict mypy passed for 580 files, all 12 import contracts passed,
  Ruff/format and startup passed, and the committed-head AIP check passed for
  14 relevant files. Targeted real PostgreSQL/payment/tenant regressions passed.
- Independent read-only reviewer verdicts and exact blob receipts are retained
  in each repository's `.superpowers/reviews/2026-11-04-*-review*.json` files.
  GitHub's separate Codex review service reported an execution failure, with no
  published review or inline threads; it is not counted as a successful review.
- Both PRs have no outstanding published inline comments or submitted reviews.
  Merge and production deployment have not been performed. Owner-only merge and
  the explicit production deployment boundary remain in effect.
