#!/usr/bin/env python3
"""Dependency-free contract checks for the public Gigma MCP plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "plugins" / "gigma-mcp"
MCP_URL = "https://api.auth.gigma.ru/mcp/owner/"
LIVE_CHECK = ROOT / "check_live_contract.py"

REQUIRED_DOCS = (
    ROOT / "docs/mcp-client-setup.md",
    ROOT / "docs/gigma-project-workflows.md",
    ROOT / "docs/gigma-user-journey.md",
    ROOT / "docs/mcp-capability-matrix.md",
    ROOT / "docs/mcp-security-and-approvals.md",
    ROOT / "docs/mcp-troubleshooting.md",
    ROOT / "docs/examples/golden-dialogues.md",
)

REQUIRED_SKILLS = (
    PACKAGE / "skills/gigma-owner-auth/SKILL.md",
    PACKAGE / "skills/gigma-owner-setup/SKILL.md",
    PACKAGE / "skills/gigma-owner-router/SKILL.md",
    PACKAGE / "skills/gigma-owner-project-ops/SKILL.md",
    PACKAGE / "skills/gigma-owner-subscriptions/SKILL.md",
    PACKAGE / "skills/gigma-owner-investigation/SKILL.md",
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+eyJ[a-zA-Z0-9._-]+"),
    re.compile(r"-----BEGIN [A-Z ]+-----"),
    re.compile(r'"(?:access_token|refresh_token|client_secret|provider_secret)"\s*:\s*"[^"]+"'),
)


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_no_secret_values(paths: tuple[Path, ...]) -> None:
    for path in paths:
        text = read_text(path)
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"secret-like value found in {path}")


def main() -> int:
    manifest_files = [
        ROOT / ".agents/plugins/marketplace.json",
        ROOT / ".claude-plugin/marketplace.json",
        ROOT / ".cursor-plugin/marketplace.json",
        PACKAGE / "plugin.json",
        PACKAGE / ".codex-plugin/plugin.json",
        PACKAGE / ".claude-plugin/plugin.json",
        PACKAGE / ".cursor-plugin/plugin.json",
        PACKAGE / "mcp.json",
    ]
    for path in manifest_files:
        if not path.is_file():
            raise FileNotFoundError(path)
        load(path)

    for path in manifest_files[:3]:
        entry = load(path)["plugins"][0]
        source = entry["source"]
        source_path = source["path"] if isinstance(source, dict) else source
        if source_path != "./plugins/gigma-mcp":
            raise ValueError(f"{path} points at {source_path!r}")

    for path in REQUIRED_DOCS + REQUIRED_SKILLS + (LIVE_CHECK,):
        if not path.is_file():
            raise FileNotFoundError(path)

    mcp = load(PACKAGE / "mcp.json")
    server = mcp["mcpServers"].get("gigma")
    if not isinstance(server, dict) or server["url"] != MCP_URL:
        raise ValueError("MCP URL mismatch")
    if server["type"] != "streamable-http":
        raise ValueError("MCP transport mismatch")
    if server["extensions"]["com.openai"]["auth"]["type"] != "none":
        raise ValueError("Native callback package must use auth.type none")

    portable = load(PACKAGE / "plugin.json")
    codex = load(PACKAGE / ".codex-plugin/plugin.json")
    claude = load(PACKAGE / ".claude-plugin/plugin.json")
    cursor = load(PACKAGE / ".cursor-plugin/plugin.json")
    for manifest in (portable, codex, claude, cursor):
        if manifest.get("name") != "gigma-mcp":
            raise ValueError("plugin manifest name mismatch")
        if manifest.get("version") != "0.2.1":
            raise ValueError("plugin manifest version mismatch")
    if codex.get("mcpServers") != "./mcp.json":
        raise ValueError("Codex MCP mapping mismatch")
    if claude.get("mcpServers", {}).get("gigma", {}).get("url") != MCP_URL:
        raise ValueError("Claude MCP URL mismatch")
    if claude.get("mcpServers", {}).get("gigma", {}).get("type") != "http":
        raise ValueError("Claude MCP transport mismatch")
    if cursor.get("mcpServers") != "./mcp.json":
        raise ValueError("Cursor MCP mapping mismatch")

    auth_skill = read_text(PACKAGE / "skills/gigma-owner-auth/SKILL.md")
    for required in (
        "erp_dialog_check",
        "erp_dialog_start",
        "erp_dialog_status",
        "erp_dialog_reconcile",
        "erp_dialog_connect",
        "erp_dialog_cancel",
        "erp_dialog_logout",
        "session_capability",
        "project_exists",
        "consent: true",
        "recovery_required",
        "exactly one consent path",
        "do not ask",
        "text fallback",
        "After `erp_dialog_start` returns",
        "not the callback number",
    ):
        if required not in auth_skill:
            raise ValueError(f"auth skill missing {required}")
    if "codex mcp login" in auth_skill and "OAuth" not in auth_skill:
        raise ValueError("skill does not explain separate OAuth mode")
    if not re.search(r"`?gigma`?\s+MCP server", auth_skill):
        raise ValueError("skill lost canonical gigma server id")

    setup_skill = read_text(PACKAGE / "skills/gigma-owner-setup/SKILL.md")
    router_skill = read_text(PACKAGE / "skills/gigma-owner-router/SKILL.md")
    if "owns the callback flow" not in setup_skill or "do not" not in setup_skill:
        raise ValueError("setup skill must delegate callback flow to auth skill")
    if "connect or register → `gigma-owner-auth`" not in router_skill:
        raise ValueError("router must route connection to auth skill only")
    if "gigma-owner-setup` + `gigma-owner-auth" in router_skill:
        raise ValueError("router must not load duplicate connection flows")

    live_check = read_text(LIVE_CHECK)
    for marker in (
        "tools/list",
        "resources/list",
        "resourceUri",
        "io.modelcontextprotocol/ui",
        "destructiveHint",
    ):
        if marker not in live_check:
            raise ValueError(f"live contract check missing {marker!r}")

    readme = read_text(ROOT / "README.md")
    package_readme = read_text(PACKAGE / "README.md")
    for document in (readme, package_readme):
        for marker in (
            MCP_URL,
            "text callback flow",
            "codex mcp login gigma",
            "check_live_contract.py",
            "exactly one `gigma` registration",
        ):
            if marker not in document:
                raise ValueError(f"README missing {marker!r}")
        if "MCP Apps" in document:
            raise ValueError("public README must not advertise MCP Apps UI")
    for marker in ("erp_dialog_check", "erp_dialog_connect"):
        if marker not in package_readme:
            raise ValueError(f"package README missing {marker!r}")
    if "docs/mcp-client-setup.md" not in readme:
        raise ValueError("root README missing client setup link")
    if "docs/gigma-project-workflows.md" not in readme:
        raise ValueError("root README missing workflow link")

    documentation = readme + package_readme + "".join(read_text(p) for p in REQUIRED_DOCS)
    if "api.auth.gigma.ru.git" in documentation:
        raise ValueError("documentation points at backend repository")
    if "arbitrary REST" not in documentation or "arbitrary SQL" not in documentation:
        raise ValueError("documentation missing arbitrary REST/SQL boundary")

    assert_no_secret_values(
        REQUIRED_DOCS
        + REQUIRED_SKILLS
        + (ROOT / "README.md", PACKAGE / "README.md", LIVE_CHECK)
    )

    print("Validation OK: Gigma MCP manifests, endpoint, text flow, docs and skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
