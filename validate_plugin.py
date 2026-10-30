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
        raise ValueError(f"{path} must contain an object")
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
    if mcp["mcpServers"]["gigma"]["url"] != MCP_URL:
        raise ValueError("MCP URL mismatch")
    if mcp["mcpServers"]["gigma"]["type"] != "streamable-http":
        raise ValueError("MCP transport mismatch")

    skill = PACKAGE / "skills/gigma-owner-auth/SKILL.md"
    text = skill.read_text(encoding="utf-8")
    for required in ("erp_dialog_check", "erp_dialog_start", "erp_dialog_status", "erp_dialog_connect", "session_capability"):
        if required not in text:
            raise ValueError(f"skill missing {required}")
    if any(secret in text.lower() for secret in ("client_secret", "access_token", "refresh_token")):
        raise ValueError("skill contains forbidden credential material")

    print("Validation OK: Gigma MCP marketplace, manifests, endpoint, and skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
