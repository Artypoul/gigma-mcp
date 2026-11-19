#!/usr/bin/env python3
"""Validate and build a Gigma MCP plugin ZIP for ChatGPT import.

The archive contains a single gigma-mcp/ directory, never the repository's
marketplaces or compatibility overlays. Source file times and permissions do
not affect the archive. The default is portable; --chatgpt-app-id builds a
private archive bound to an already registered App. Building does not install
or authenticate the plugin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import tempfile
import zipfile

import validate_plugin

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "plugins" / "gigma-mcp"
ROOT_FILES = ("plugin.json", "mcp.json", "README.md", "LICENSE", "check_live_contract.py")
COMPONENT_DIRECTORIES = ("skills", "docs", "assets")
IGNORED_DIRECTORIES = {"__pycache__", "node_modules", "dist", "build"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".swp", ".swo", ".tmp", ".zip", ".tar", ".gz"}
SECRET_FILENAMES = {
    "credentials.json", "secrets.json", "secrets.yaml", "secrets.yml",
    "token.json", "tokens.json",
}
SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".ini", ".cfg"}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _package_paths(package: Path) -> list[Path]:
    """Select portable components without following any selected symlink."""
    if package.is_symlink() or package.parent.is_symlink():
        raise ValueError("plugin directory must not be a symlink")
    paths: list[Path] = []

    def visit(path: Path) -> None:
        if path.is_symlink():
            raise ValueError(f"symlinks are not allowed in the package: {path}")
        if path.name.startswith("."):
            return
        if path.is_dir():
            if path.name not in IGNORED_DIRECTORIES:
                for child in sorted(path.iterdir()):
                    visit(child)
            return
        if not path.is_file():
            raise ValueError(f"package entry is not a regular file: {path}")
        if path.name.lower() in SECRET_FILENAMES or path.suffix.lower() in SECRET_SUFFIXES:
            raise ValueError(f"credential file must not be packaged: {path}")
        if path.suffix.lower() not in IGNORED_SUFFIXES:
            paths.append(path)

    for name in ROOT_FILES:
        path = package / name
        if not path.exists() and not path.is_symlink():
            raise ValueError(f"required package file is missing: {name}")
        visit(path)
    for name in COMPONENT_DIRECTORIES:
        path = package / name
        if path.exists() or path.is_symlink():
            if not path.is_symlink() and not path.is_dir():
                raise ValueError(f"package component must be a directory: {name}")
            visit(path)
    return sorted(paths)


def _snapshot(package: Path, paths: list[Path]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in paths:
        relative = path.relative_to(package).as_posix()
        content = path.read_bytes()
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = content.decode("utf-8")
            for pattern in validate_plugin.SECRET_VALUE_PATTERNS:
                if pattern.search(text):
                    raise ValueError(f"secret-like value must not be packaged: {relative}")
        files[relative] = content
    return files


def _check_isolated_links(files: dict[str, bytes]) -> None:
    """Check links against exactly the files that will survive packaging."""
    with tempfile.TemporaryDirectory(prefix="gigma-package-check-") as directory:
        package = Path(directory) / "gigma-mcp"
        for relative, content in files.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        validate_plugin.validate_packaged_links(package)


def build_package(output: Path | None = None, chatgpt_app_id: str | None = None) -> Path:
    if chatgpt_app_id is not None and not re.fullmatch(
        r"(?:asdk_app_|connector_|templated_apps_)[A-Za-z0-9][A-Za-z0-9_-]*", chatgpt_app_id
    ):
        raise ValueError("invalid ChatGPT App ID: expected a supported prefix and safe suffix")
    # Check selected paths before validators or readers can traverse a symlink.
    paths = _package_paths(PACKAGE)
    if validate_plugin.main() != 0:
        raise ValueError("plugin validation failed")
    files = _snapshot(PACKAGE, paths)
    manifest = json.loads(files["plugin.json"])
    if manifest.get("extensions", {}).get("com.openai", {}).get("apps") is not None:
        raise ValueError("app-bound plugins require a separate archive including .app.json")
    if chatgpt_app_id is not None:
        manifest.setdefault("extensions", {}).setdefault("com.openai", {})["apps"] = "./.app.json"
        files["plugin.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        files[".app.json"] = (json.dumps(
            {"apps": {"gigma": {"id": chatgpt_app_id, "required": True}}}, indent=2
        ) + "\n").encode("utf-8")
        del files["mcp.json"]
    name, version = manifest["name"], manifest["version"]
    if name != PACKAGE.name or not isinstance(version, str) or any(
        character not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-+"
        for character in version
    ):
        raise ValueError("plugin name/version cannot form a safe archive path")
    destination = (
        Path(output) if output is not None
        else ROOT / "dist" / f"{name}-{version}-chatgpt{'-app' if chatgpt_app_id is not None else ''}.zip"
    ).absolute()
    if destination.is_symlink():
        raise ValueError("archive output must not be a symlink")
    if destination.resolve().is_relative_to(PACKAGE.resolve()):
        raise ValueError("archive output must be outside the plugin directory")
    if destination.suffix.lower() != ".zip":
        raise ValueError("archive output must have a .zip extension")
    _check_isolated_links(files)

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, content in sorted(files.items()):
                entry = zipfile.ZipInfo(f"{name}/{relative}", date_time=ZIP_TIMESTAMP)
                entry.create_system = 3
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(
                    entry, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
                )
        with zipfile.ZipFile(temporary) as archive:
            expected = {f"{name}/{relative}": content for relative, content in files.items()}
            if archive.testzip() is not None or set(archive.namelist()) != set(expected):
                raise ValueError("built archive failed its content check")
            if any(archive.read(path) != content for path, content in expected.items()):
                raise ValueError("built archive differs from its source snapshot")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        help=("ZIP path outside the plugin directory (default: "
              "dist/<name>-<version>-chatgpt.zip, or -chatgpt-app.zip when bound)"),
    )
    parser.add_argument(
        "--chatgpt-app-id",
        help=("build a private archive bound to an already registered Gigma App ID "
              "(asdk_app_, connector_, or templated_apps_ prefix). Syntax validation "
              "does not verify registration or ownership."),
    )
    args = parser.parse_args()
    try:
        archive = build_package(args.output, args.chatgpt_app_id)
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Package build failed: {exc}")
        return 1
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"Built {archive} ({archive.stat().st_size} bytes)")
    print(f"SHA256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
