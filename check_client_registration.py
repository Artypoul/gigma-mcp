#!/usr/bin/env python3
"""Check a package with the real Codex loader, without installing or logging in.

Only app-server initialize and plugin/read requests are sent. Each read uses a
temporary, single-plugin marketplace and a package copy. No model turn, MCP
tools/call, plugin installation, or owner authentication is performed. HOME,
CODEX_HOME and the user's configuration are not changed. Run on a clean CI
runner to avoid unrelated host startup requirements.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "gigma-mcp"
EXPECTED_SKILLS = {
    "gigma-owner-auth", "gigma-owner-investigation", "gigma-owner-project-ops",
    "gigma-owner-router", "gigma-owner-setup", "gigma-owner-subscriptions",
}
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


class CheckFailure(Exception):
    """An intentionally safe, user-facing diagnostic."""


def safe_diagnostic(text: str) -> str:
    """Classify errors without printing paths, credentials or session payloads."""
    value = text.lower()
    if "unknown field" in value and "extensions" in value:
        return "MCP parser rejected the unsupported extensions field"
    if "sqlite" in value and any(s in value for s in ("failed", "unable", "error")):
        return "Codex could not initialize its SQLite runtime"
    if "read-only file system" in value:
        return "Codex startup requires a writable runtime path (read-only filesystem)"
    if "permission denied" in value or "operation not permitted" in value:
        return "Codex runtime access was denied"
    if "failed to parse plugin mcp" in value:
        return "Codex reported a plugin MCP parse error"
    if "failed to" in value and any(s in value for s in ("skill", "plugin", "manifest")):
        return "Codex reported a plugin component loading error"
    return "Codex returned an error; raw diagnostics suppressed"


def copy_package(source: Path, destination: Path) -> None:
    if not source.is_dir() or source.is_symlink():
        raise CheckFailure("Package must be a regular directory")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise CheckFailure("Package copy refuses symbolic links")
    shutil.copytree(source, destination)


def unpack_archive(archive_path: Path, destination: Path) -> Path:
    """Extract the actual ZIP, rejecting traversal, links and duplicate paths."""
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if sum(member.file_size for member in members) > MAX_ARCHIVE_BYTES:
            raise CheckFailure("Unpacked archive exceeds the 64 MiB probe limit")
        seen: set[str] = set()
        roots: set[str] = set()
        for member in members:
            name = member.filename
            path = PurePosixPath(name)
            mode = stat.S_IFMT(member.external_attr >> 16)
            if (
                not path.parts or path.is_absolute() or ".." in path.parts
                or "\\" in name or ":" in name or path.as_posix() in seen
                or mode not in (0, stat.S_IFREG, stat.S_IFDIR)
            ):
                raise CheckFailure("Archive contains an unsafe or duplicate entry")
            seen.add(path.as_posix())
            roots.add(path.parts[0])
        if roots != {PLUGIN_NAME}:
            raise CheckFailure("Archive must contain exactly one gigma-mcp directory")
        archive.extractall(destination)
    return destination / PLUGIN_NAME


def prepare_marketplace(source: Path, root: Path, *, regression: bool) -> Path:
    package = root / PLUGIN_NAME
    copy_package(source, package)
    manifest = json.loads((package / "plugin.json").read_text(encoding="utf-8"))
    if manifest.get("name") != PLUGIN_NAME:
        raise CheckFailure("Input does not identify the gigma-mcp plugin")
    if regression:
        path = package / "mcp.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["mcpServers"]["gigma"]["extensions"] = {
            "com.openai": {"auth": {"type": "none"}}
        }
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    marketplace = root / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(json.dumps({
        "name": "gigma-registration-probe-" + ("regression" if regression else "candidate"),
        "plugins": [{
            "name": PLUGIN_NAME,
            "source": {"source": "local", "path": "./gigma-mcp"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
        }],
    }), encoding="utf-8")
    return marketplace


def read_with_codex(codex: str, marketplace: Path, runtime: Path, timeout: float) -> tuple[dict, list[str]]:
    for name in ("state", "logs"):
        (runtime / name).mkdir(parents=True, exist_ok=True)
    command = [
        codex, "app-server", "--stdio",
        "-c", "features.plugins=true",
        "-c", "analytics.enabled=false",
        "-c", 'history.persistence="none"',
        "-c", "plugins._default.enabled=false",
        "-c", "sqlite_home=" + json.dumps(str(runtime / "state")),
        "-c", "log_dir=" + json.dumps(str(runtime / "logs")),
    ]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, cwd=runtime, start_new_session=os.name == "posix",
    )
    messages: queue.Queue[object] = queue.Queue(maxsize=64)
    exceeded = threading.Event()
    stderr = bytearray()

    def read_stdout() -> None:
        total = 0
        assert process.stdout is not None
        while line := process.stdout.readline(MAX_OUTPUT_BYTES + 1):
            total += len(line)
            if total > MAX_OUTPUT_BYTES:
                exceeded.set()
                return
            try:
                item: object = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                item = CheckFailure("Codex stdout was not valid JSON-RPC")
            try:
                messages.put_nowait(item)
            except queue.Full:
                exceeded.set()
                return

    def read_stderr() -> None:
        assert process.stderr is not None
        while data := process.stderr.read(4096):
            stderr.extend(data)
            del stderr[:-65536]

    readers = [threading.Thread(target=read_stdout, daemon=True), threading.Thread(target=read_stderr, daemon=True)]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + timeout

    def send(message: dict) -> None:
        assert process.stdin is not None
        try:
            process.stdin.write((json.dumps(message) + "\n").encode())
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise CheckFailure(safe_diagnostic(stderr.decode(errors="replace"))) from exc

    def receive(request_id: int) -> dict:
        while time.monotonic() < deadline:
            if exceeded.is_set():
                raise CheckFailure("Codex output exceeded the bounded probe limit")
            try:
                message = messages.get(timeout=min(0.1, max(0.001, deadline - time.monotonic())))
            except queue.Empty:
                if process.poll() is not None:
                    readers[1].join(timeout=0.2)
                    raise CheckFailure(safe_diagnostic(stderr.decode(errors="replace")))
                continue
            if isinstance(message, CheckFailure):
                raise message
            if not isinstance(message, dict):
                raise CheckFailure("Codex returned a malformed JSON-RPC message")
            if "method" in message and "id" in message:
                raise CheckFailure("Codex requested a client action; the probe cannot authenticate or approve actions")
            if message.get("id") == request_id:
                return message
        raise CheckFailure("Codex app-server timed out before registration could be verified")

    response: dict
    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "gigma_registration_probe", "version": "1.0.0"},
            "capabilities": {"experimentalApi": True, "explicitGatewayOauth": True},
        }})
        initialized = receive(1)
        if "result" not in initialized:
            raise CheckFailure("Codex initialize failed: " + safe_diagnostic(json.dumps(initialized.get("error", {}))))
        send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "plugin/read", "params": {
            "marketplacePath": str(marketplace), "pluginName": PLUGIN_NAME,
        }})
        response = receive(2)
    finally:
        # Terminate only our own process group, including inherited pipe owners.
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=3)
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for reader in readers:
            reader.join(timeout=0.3)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
    diagnostics = []
    for line in stderr.decode(errors="replace").splitlines():
        lower = line.lower()
        if ("failed to" in lower and any(s in lower for s in ("plugin", "skill", "manifest"))) or "unknown field" in lower:
            diagnostics.append(safe_diagnostic(line))
    return response, sorted(set(diagnostics))


def check_result(response: dict, diagnostics: list[str], *, regression: bool) -> dict:
    case = "regression" if regression else "candidate"
    if "error" in response:
        reason = safe_diagnostic(json.dumps(response["error"]))
        if regression and reason == "MCP parser rejected the unsupported extensions field":
            return {"case": case, "status": "passed", "mcp_count": 0, "component_errors": [reason]}
        raise CheckFailure(f"{case}: plugin/read failed: {reason}")
    result = response.get("result")
    plugin = result.get("plugin") if isinstance(result, dict) else None
    if not isinstance(plugin, dict) or plugin.get("summary", {}).get("name") != PLUGIN_NAME:
        raise CheckFailure(f"{case}: plugin/read did not return the requested plugin")
    servers, skills = plugin.get("mcpServers"), plugin.get("skills")
    if not isinstance(servers, list) or not all(isinstance(name, str) for name in servers) or not isinstance(skills, list):
        raise CheckFailure(f"{case}: plugin/read returned malformed component lists")
    skill_names = [skill.get("name") if isinstance(skill, dict) else None for skill in skills]
    expected_names = {f"{PLUGIN_NAME}:{name}" for name in EXPECTED_SKILLS}
    if len(skill_names) != 6 or set(skill_names) not in (EXPECTED_SKILLS, expected_names):
        raise CheckFailure(f"{case}: expected all six Gigma skills; loader returned {len(skill_names)} entries")
    component_errors = [key for key in ("errors", "componentErrors", "loadErrors") if plugin.get(key)]
    if regression:
        if "gigma" in servers or servers:
            raise CheckFailure("regression: loader accepted the old unsupported MCP declaration")
    elif servers != ["gigma"] or diagnostics or component_errors:
        raise CheckFailure(
            f"candidate: expected MCP ['gigma'] and no component errors; "
            f"got {len(servers)} server(s), gigma_present={'gigma' in servers}, "
            f"component_errors={len(diagnostics) + len(component_errors)}"
        )
    return {
        "case": case, "status": "passed", "mcp_servers": servers,
        "mcp_count": len(servers), "skill_count": len(skills),
        "component_errors": diagnostics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--package", type=Path, default=ROOT / "plugins" / PLUGIN_NAME)
    inputs.add_argument("--archive", type=Path, help="Built single-plugin ZIP to check")
    parser.add_argument("--codex", default="codex", help="Codex executable (CI must pin its version)")
    parser.add_argument("--timeout", type=float, default=20, help="Maximum seconds per app-server process (1–60)")
    parser.add_argument("--regression-check", action="store_true", help="First prove the loader rejects the old server extensions block")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60 seconds")
    try:
        codex = shutil.which(args.codex)
        if codex is None:
            raise CheckFailure("Codex executable not found; install the pinned CI version")
        version = subprocess.run([codex, "--version"], capture_output=True, timeout=min(args.timeout, 5), check=True)
        match = re.search(rb"codex-cli ([0-9][A-Za-z0-9.+-]*)", version.stdout)
        if match is None:
            raise CheckFailure("Could not identify the Codex CLI version")
        print("Codex loader: " + match.group(1).decode(), flush=True)
        with tempfile.TemporaryDirectory(prefix="gigma-registration-") as directory:
            temporary = Path(directory)
            source = unpack_archive(args.archive, temporary / "archive") if args.archive else args.package.absolute()
            for regression in ([True, False] if args.regression_check else [False]):
                case = "regression" if regression else "candidate"
                marketplace = prepare_marketplace(source, temporary / case, regression=regression)
                response, diagnostics = read_with_codex(codex, marketplace, temporary / (case + "-runtime"), args.timeout)
                print(json.dumps(check_result(response, diagnostics, regression=regression), sort_keys=True), flush=True)
        print("Registration OK: real Codex loader found gigma and all six skills; owner login was not tested")
        return 0
    except CheckFailure as exc:
        print(f"Registration FAILED: {exc}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, zipfile.BadZipFile, subprocess.SubprocessError):
        print("Registration FAILED: package input or Codex process could not be read; raw details suppressed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
