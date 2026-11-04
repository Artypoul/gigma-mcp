# Gigma MCP development and release runbook

## Local verification environment

The owner-approved location for installing dependencies, running projects and
testing is `D:\Development\gigma-auth`. Repository source stays in the existing
Git checkouts; generated logs, service data, credentials and virtual environments
belong in that test directory, never in either repository.

The backend checkout used by this workspace is
`C:\Users\Art\Documents\GitHub\api.auth.gigma.ru`; the distribution checkout is
`C:\Users\Art\Documents\GitHub\gigma-mcp`.

Use `D:\Development\gigma-auth\.venv\Scripts\python.exe` for backend tests.
The current native review stack lives under
`D:\Development\gigma-auth\review`, independently of preserved legacy service
data. It uses PostgreSQL 17.11 on `127.0.0.1:15432`, Redis 7.2.16 on
`127.0.0.1:16379` and MinIO on loopback ports `19000/19001`.

In PowerShell 7, inspect and reuse the owned processes:

```powershell
& 'D:\Development\gigma-auth\review\services.ps1' -Action status
& 'D:\Development\gigma-auth\review\services.ps1' -Action start
& 'D:\Development\gigma-auth\review\test-services.ps1'
```

The helper checks every listener, executable, command, PID and creation time
against `review\service-ownership.json`; PostgreSQL also checks its exact
`review\postgres-data` and `postmaster.pid`. It fails closed on a foreign port,
reused PID, unrecorded process or unresolved startup. Background windows stay
hidden. `test-services.ps1` checks ownership failures without starting or
stopping services. The API itself is not launched by this dependency helper.

Run a selected backend suite through the dedicated launcher:

```powershell
& 'D:\Development\gigma-auth\.venv\Scripts\python.exe' -B 'D:\Development\gigma-auth\review\run-tests.py' tests/test_mcp_dialog.py tests/test_mcp_owner_business_db.py
```

It binds PostgreSQL to the isolated `gigma_auth_review_test` database, Redis to
DB 4 and S3 to the review MinIO, loading synthetic credentials locally without
printing them. Logs, JUnit and temporary test files stay under `review`.
Do not run DB/schema suites concurrently against the same test database.

After all tests and uses of the stack have finished:

```powershell
& 'D:\Development\gigma-auth\review\services.ps1' -Action stop
```

Stop checks for active Python pytest/launcher processes, then stops only owned
PIDs; PostgreSQL uses `pg_ctl` with the exact review data directory. It never
erases a data directory. Inspect status and logs after an uncertain result
before another action. The old root `start-local.ps1`, `stop-local.ps1` and
`run-pr-tests.py` retain their legacy paths and are not current launchers.
See the local `D:\Development\gigma-auth\README.md` for the current environment;
historical numeric results do not prove the state of the current checkout.

## Package checks

From this distribution checkout:

```powershell
python -B validate_plugin.py
python -B -m unittest discover -s tests -v
python -B check_live_contract.py
```

The live check uses only public MCP initialization and metadata discovery. It
does not authorize or execute callback, business or payment operations. A pass
proves metadata compatibility, not delivery, database recovery or deployment.

## Release verification

Run the backend's relevant unit and PostgreSQL tests in the local environment,
then check the packaged documentation and native contract together. Record the
exact Git revisions and actual results. Inspect required backend PR checks on
the latest head and follow the backend's existing manual release procedure.
Do not equate the MCP SDK version in `serverInfo` with a deployed Git revision.

Never copy capabilities, owner sessions, credentials or local service secrets
into evidence, PRs or the plugin package.
