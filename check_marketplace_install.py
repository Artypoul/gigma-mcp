#!/usr/bin/env python3
"""Install the real Gigma marketplace on a clean, disposable GitHub CI runner.

This deliberately writes the runner's normal Codex config/cache. It never changes
HOME or CODEX_HOME and refuses an existing configuration, login, or plugin cache.
Only marketplace/plugin CLI operations and the existing read-only plugin loader
probe run: no model turn, owner login, MCP tools/call, or uninstall is performed.

Codex JSON fields are defined by cli/src/{marketplace_cmd,plugin_cmd}.rs:
https://github.com/openai/codex/blob/main/codex-rs/cli/src/marketplace_cmd.rs
https://github.com/openai/codex/blob/main/codex-rs/cli/src/plugin_cmd.rs
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit

from check_client_registration import (
    CheckFailure, EXPECTED_SKILLS, MARKETPLACE_RELATIVE, PACKAGE_RELATIVE,
    PLUGIN_NAME, check_result, prepare_marketplace, read_with_codex,
    safe_diagnostic,
)

ROOT = Path(__file__).resolve().parent
PLUGIN_ID = f"{PLUGIN_NAME}@{PLUGIN_NAME}"
MCP_URL = "https://api.auth.gigma.ru/mcp/owner/"
MAX_OUTPUT = 2 * 1024 * 1024
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?")


def require_clean_ci(ci_only: bool, environment: dict[str, str], home: Path) -> tuple[Path, Path]:
    if not ci_only or any(environment.get(key) != "true" for key in ("CI", "GITHUB_ACTIONS")):
        raise CheckFailure("Install probe requires --ci-only on a disposable GitHub Actions runner")
    runner = environment.get("RUNNER_TEMP")
    if not runner or not Path(runner).is_absolute() or not Path(runner).is_dir():
        raise CheckFailure("Install probe needs the runner's existing temporary directory")
    runner_root = Path(runner).resolve()
    home = home.resolve()
    configured_home = environment.get("CODEX_HOME")
    codex_root = Path(configured_home).expanduser() if configured_home else home / ".codex"
    if not codex_root.is_absolute() or codex_root.is_symlink():
        raise CheckFailure("Codex runtime path is not a regular absolute path")
    codex_root = codex_root.resolve()
    if not any(codex_root.is_relative_to(root) and codex_root != root for root in (home, runner_root)):
        raise CheckFailure("Codex runtime must stay inside the runner's home or temporary directory")
    protected = [codex_root / name for name in ("config.toml", "auth.json", "plugins")]
    protected.append(home / ".agents/plugins/marketplace.json")
    if any(path.exists() or path.is_symlink() for path in protected):
        raise CheckFailure("Install probe refuses an existing Codex config, login, or plugin cache")
    return codex_root, runner_root


def select_source(source: str, revision: str | None, environment: dict[str, str]) -> tuple[str, str]:
    if source.startswith("https://"):
        parsed = urlsplit(source)
        if (parsed.netloc != "github.com" or parsed.query or parsed.fragment
                or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", parsed.path)):
            raise CheckFailure("Remote source must be a plain HTTPS GitHub repository URL")
        if not revision or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            raise CheckFailure("Remote install requires --ref with the full published commit SHA")
        source = source.rstrip("/")
        return "git", source if source.endswith(".git") else source + ".git"
    if revision is not None:
        raise CheckFailure("Local checkout mode does not accept --ref")
    candidate = Path(source)
    if not candidate.is_dir() or candidate.is_symlink():
        raise CheckFailure("Local source must be an existing regular checkout directory")
    candidate = candidate.resolve()
    roots = [Path(environment[key]).resolve() for key in ("GITHUB_WORKSPACE", "RUNNER_TEMP")
             if environment.get(key)]
    if not any(candidate.is_relative_to(root) for root in roots):
        raise CheckFailure("Local source must be inside the disposable runner checkout or temporary directory")
    return "local", str(candidate)


def run_bounded(command: list[str], *, cwd: Path, timeout: float, stage: str) -> str:
    """Bound both pipes and the whole child process group; never echo raw output."""
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=environment, start_new_session=os.name == "posix")
    buffers = [bytearray(), bytearray()]
    exceeded = threading.Event()

    def collect(stream, target: bytearray) -> None:
        while chunk := stream.read(4096):
            if len(target) + len(chunk) > MAX_OUTPUT:
                exceeded.set()
                return
            target.extend(chunk)

    readers = [threading.Thread(target=collect, args=(stream, target), daemon=True)
               for stream, target in zip((process.stdout, process.stderr), buffers)]
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + timeout
    failure = None
    try:
        while process.poll() is None:
            if exceeded.is_set():
                failure = "output exceeded the probe limit"
                break
            if time.monotonic() >= deadline:
                failure = "timed out"
                break
            time.sleep(0.02)
    finally:
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
            reader.join(timeout=0.5)
        for stream in (process.stdout, process.stderr):
            stream.close()
    if failure or exceeded.is_set():
        raise CheckFailure(f"{stage}: {failure or 'output exceeded the probe limit'}")
    if process.returncode != 0:
        raise CheckFailure(f"{stage}: " + safe_diagnostic(buffers[1].decode(errors="replace")))
    try:
        return buffers[0].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CheckFailure(f"{stage}: output was not UTF-8") from exc


def run_json(command: list[str], *, cwd: Path, timeout: float, stage: str) -> dict:
    try:
        result = json.loads(run_bounded(command, cwd=cwd, timeout=timeout, stage=stage))
    except ValueError as exc:
        raise CheckFailure(f"{stage}: CLI did not return a JSON object") from exc
    if not isinstance(result, dict):
        raise CheckFailure(f"{stage}: CLI did not return a JSON object")
    return result


def returned_directory(value: object, roots: tuple[Path, ...]) -> Path:
    if not isinstance(value, str) or "\x00" in value:
        raise CheckFailure("CLI returned an invalid installation path")
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise CheckFailure("CLI returned a missing or non-regular installation directory")
    path = path.resolve()
    if not any(path.is_relative_to(root) for root in roots):
        raise CheckFailure("CLI installation path escapes the trusted runner directory")
    return path


def load_json_file(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_OUTPUT:
        raise CheckFailure("Installed package contains a missing or unsafe JSON file")
    try:
        value = json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError) as exc:
        raise CheckFailure("Installed package contains invalid JSON") from exc
    if not isinstance(value, dict):
        raise CheckFailure("Installed package JSON must contain an object")
    return value


def inspect_package(package: Path, expected_version: str) -> dict[str, bytes]:
    if any(path.is_symlink() for path in package.rglob("*")):
        raise CheckFailure("Installed package contains a symbolic link")
    manifest = load_json_file(package / "plugin.json")
    if manifest.get("name") != PLUGIN_NAME or manifest.get("version") != expected_version:
        raise CheckFailure("Installed manifest identity or version does not match this checkout")
    mcp = load_json_file(package / "mcp.json")
    servers = mcp.get("mcpServers")
    if (not isinstance(servers, dict) or set(servers) != {"gigma"}
            or servers["gigma"] != {"type": "streamable-http", "url": MCP_URL}):
        raise CheckFailure("Installed package must contain exactly the canonical Gigma MCP server")
    skill_files = list((package / "skills").glob("*/SKILL.md"))
    if len(skill_files) != 6 or {path.parent.name for path in skill_files} != EXPECTED_SKILLS:
        raise CheckFailure("Installed package does not contain all six Gigma skills")
    files = [package / "plugin.json", package / "mcp.json", *skill_files]
    if any(not path.is_file() or path.stat().st_size > MAX_OUTPUT for path in files):
        raise CheckFailure("Installed component exceeds the safe probe size")
    return {path.relative_to(package).as_posix(): path.read_bytes() for path in files}


def check_provenance(record: dict, source_type: str, source: str) -> bool:
    provenance = record.get("marketplaceSource")
    if provenance is None:
        return False  # Older clients may omit this optional field.
    if provenance != {"sourceType": source_type, "source": source}:
        raise CheckFailure("CLI marketplace provenance does not match the requested source")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci-only", action="store_true", help="Allow installing into a clean disposable CI runner")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--source", default="https://github.com/Artypoul/gigma-mcp.git")
    parser.add_argument("--ref", dest="revision", help="Full published commit SHA; remote source only")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.timeout <= 300:
            raise CheckFailure("Timeout must be between 1 and 300 seconds per operation")
        environment = dict(os.environ)
        codex_root, runner_root = require_clean_ci(args.ci_only, environment, Path.home())
        source_type, source = select_source(args.source, args.revision, environment)
        version = load_json_file(ROOT / PACKAGE_RELATIVE / "plugin.json").get("version")
        if not isinstance(version, str) or not SEMVER.fullmatch(version):
            raise CheckFailure("The checkout must declare a semantic plugin version")
        codex = shutil.which(args.codex)
        if not codex:
            raise CheckFailure("Codex CLI was not found")
        command = [codex, "-c", "features.plugins=true", "-c", "analytics.enabled=false", "plugin"]
        with tempfile.TemporaryDirectory(prefix="gigma-install-probe-", dir=runner_root) as directory:
            temporary = Path(directory)
            def call(arguments: list[str], stage: str) -> dict:
                return run_json(command + arguments, cwd=temporary, timeout=args.timeout, stage=stage)
            add_args = ["marketplace", "add", source, "--json"]
            if args.revision:
                add_args.extend(["--ref", args.revision])
            added = call(add_args, "marketplace add")
            if added.get("marketplaceName") != PLUGIN_NAME or added.get("alreadyAdded") is not False:
                raise CheckFailure("Marketplace install did not create a fresh Gigma marketplace")
            roots = (codex_root,) if source_type == "git" else (Path(source),)
            marketplace_root = returned_directory(added.get("installedRoot"), roots)
            if source_type == "local" and marketplace_root != Path(source):
                raise CheckFailure("Local marketplace resolved to an unexpected directory")
            if source_type == "git":
                revision = run_bounded(["git", "-C", str(marketplace_root), "rev-parse", "--verify", "HEAD"],
                                       cwd=temporary, timeout=args.timeout, stage="marketplace commit check").strip()
                if revision.lower() != args.revision.lower():
                    raise CheckFailure("Downloaded marketplace is not the requested published commit")
            catalog = load_json_file(marketplace_root / MARKETPLACE_RELATIVE)
            entries = catalog.get("plugins")
            if (catalog.get("name") != PLUGIN_NAME or not isinstance(entries, list) or len(entries) != 1
                    or not isinstance(entries[0], dict)
                    or entries[0].get("name") != PLUGIN_NAME
                    or entries[0].get("source") != {"source": "local", "path": "./plugins/gigma-mcp"}
                    or not isinstance(entries[0].get("policy"), dict)
                    or entries[0].get("policy", {}).get("authentication") != "ON_USE"):
                raise CheckFailure("Downloaded marketplace does not declare the expected Gigma package and ON_USE policy")
            source_package = returned_directory(str(marketplace_root / PACKAGE_RELATIVE), (marketplace_root,))
            original_files = inspect_package(source_package, version)
            installed = call(["add", PLUGIN_ID, "--json"], "plugin add")
            expected = {"pluginId": PLUGIN_ID, "name": PLUGIN_NAME, "marketplaceName": PLUGIN_NAME,
                        "version": version, "authPolicy": "ON_USE"}
            if any(installed.get(key) != value for key, value in expected.items()):
                raise CheckFailure("Plugin install returned an unexpected identity, version, or authentication policy")
            cached = returned_directory(installed.get("installedPath"), (codex_root,))
            if inspect_package(cached, version) != original_files:
                raise CheckFailure("Cached plugin components differ from the selected marketplace package")
            listing = call(["list", "--marketplace", PLUGIN_NAME, "--json"], "plugin list")
            records = listing.get("installed")
            if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
                raise CheckFailure("CLI does not report exactly one installed Gigma plugin")
            record = records[0]
            if (any(record.get(key) != value for key, value in expected.items())
                    or record.get("installed") is not True or record.get("enabled") is not True):
                raise CheckFailure("CLI did not persist the expected enabled Gigma plugin")
            if record.get("source") != {"source": "local", "path": str(source_package)}:
                raise CheckFailure("CLI plugin source does not match the downloaded marketplace package")
            provenance_reported = check_provenance(record, source_type, source)
            marketplace = prepare_marketplace(cached, temporary / "loader", regression=False)
            response, diagnostics = read_with_codex(codex, marketplace, temporary / "runtime", args.timeout)
            check_result(response, diagnostics, regression=False, expected_version=version)
            print(json.dumps({"status": "passed", "plugin": PLUGIN_ID, "version": version,
                              "source_type": source_type, "commit_verified": source_type == "git",
                              "provenance_reported": provenance_reported, "cache_matches_source": True,
                              "mcp_count": 1, "skill_count": 6, "owner_login_attempted": False}))
        return 0
    except (CheckFailure, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, CheckFailure) else "Install probe encountered a local execution or file error"
        print(json.dumps({"status": "failed", "reason": reason}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
