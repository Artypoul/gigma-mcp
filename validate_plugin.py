#!/usr/bin/env python3
"""Dependency-free contract checks for the public Gigma MCP plugin."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "plugins" / "gigma-mcp"
MCP_URL = "https://api.auth.gigma.ru/mcp/owner"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def main() -> int:
    files = [
        ROOT / ".agents/plugins/marketplace.json",
        ROOT / ".claude-plugin/marketplace.json",
        ROOT / ".cursor-plugin/marketplace.json",
        PACKAGE / "plugin.json",
        PACKAGE / ".codex-plugin/plugin.json",
        PACKAGE / ".claude-plugin/plugin.json",
        PACKAGE / ".cursor-plugin/plugin.json",
        PACKAGE / "mcp.json",
    ]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        load(path)

    for path in files[:3]:
        entry = load(path)["plugins"][0]
        source = entry["source"]
        source_path = source["path"] if isinstance(source, dict) else source
        if source_path != "./plugins/gigma-mcp":
            raise ValueError(f"{path} points at {source_path!r}")

    mcp = load(PACKAGE / "mcp.json")
    server = mcp["mcpServers"].get("gigma")
    if not isinstance(server, dict) or server["url"] != MCP_URL:
        raise ValueError("MCP URL mismatch")
    if server["type"] != "streamable-http":
        raise ValueError("MCP transport mismatch")
    if server["extensions"]["com.openai"]["auth"]["type"] != "none":
        raise ValueError("Codex must use Native callback without OAuth login")

    portable = load(PACKAGE / "plugin.json")
    codex = load(PACKAGE / ".codex-plugin/plugin.json")
    claude = load(PACKAGE / ".claude-plugin/plugin.json")
    cursor = load(PACKAGE / ".cursor-plugin/plugin.json")
    for manifest in (portable, codex, claude, cursor):
        if manifest.get("name") != "gigma-mcp":
            raise ValueError("plugin manifest name mismatch")
        if manifest.get("version") != "0.1.1":
            raise ValueError("plugin manifest version mismatch")
    if codex.get("mcpServers") != "./mcp.json":
        raise ValueError("Codex MCP mapping mismatch")
    if claude.get("mcpServers", {}).get("gigma", {}).get("url") != MCP_URL:
        raise ValueError("Claude MCP URL mismatch")
    if claude.get("mcpServers", {}).get("gigma", {}).get("type") != "http":
        raise ValueError("Claude MCP transport mismatch")
    if cursor.get("mcpServers") != "./mcp.json":
        raise ValueError("Cursor MCP mapping mismatch")

    skill = PACKAGE / "skills/gigma-owner-auth/SKILL.md"
    text = skill.read_text(encoding="utf-8")
    for required in (
        "erp_dialog_check",
        "erp_dialog_start",
        "erp_dialog_status",
        "erp_dialog_reconcile",
        "erp_dialog_connect",
        "erp_dialog_cancel",
        "erp_dialog_logout",
        "session_capability",
    ):
        if required not in text:
            raise ValueError(f"skill missing {required}")
    if "codex mcp login" in text and "OAuth" not in text:
        raise ValueError("skill does not explain the separate OAuth mode")
    if "Use the `gigma` MCP server" not in text:
        raise ValueError("skill lost the canonical gigma MCP server id")
    if any(
        secret in text.lower()
        for secret in ("client_secret", "access_token", "refresh_token")
    ):
        raise ValueError("skill contains forbidden credential material")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "https://github.com/Artypoul/gigma-mcp.git" not in readme:
        raise ValueError("README missing public repository install URL")
    if "codex mcp remove gigma" not in readme or "codex mcp login gigma" not in readme:
        raise ValueError("README missing stale OAuth server migration guidance")
    if "api.auth.gigma.ru.git" in readme:
        raise ValueError("README points users at the backend repository")

    print("Validation OK: Gigma MCP marketplace, manifests, endpoint, and skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
