#!/usr/bin/env python3
"""Bundle canonical docs and the read-only probe into the installed plugin.

Edit docs/ or check_live_contract.py and run this script; never edit generated copies.
Internal Superpowers plans/specifications are not distributed to users.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs"
DESTINATION = ROOT / "plugins/gigma-mcp/docs"


def sync_docs(
    *,
    source: Path = SOURCE,
    destination: Path = DESTINATION,
    check: bool = False,
) -> list[str]:
    expected = {
        path.relative_to(source): path.read_bytes()
        for path in source.rglob("*.md")
        if "superpowers" not in path.relative_to(source).parts
    }
    existing = {path.relative_to(destination) for path in destination.rglob("*.md")}
    changed = []
    for relative in sorted(expected.keys() | existing):
        target = destination / relative
        content = expected.get(relative)
        if content is None or not target.is_file() or target.read_bytes() != content:
            changed.append(relative.as_posix())
            if not check:
                if content is None:
                    target.unlink()
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
    return changed


def sync_bundle(*, root: Path = ROOT, check: bool = False) -> list[str]:
    package = root / "plugins/gigma-mcp"
    changed = [
        f"docs/{path}"
        for path in sync_docs(
            source=root / "docs", destination=package / "docs", check=check
        )
    ]
    probe = root / "check_live_contract.py"
    installed_probe = package / probe.name
    content = probe.read_bytes()
    if not installed_probe.is_file() or installed_probe.read_bytes() != content:
        changed.append(probe.name)
        if not check:
            installed_probe.parent.mkdir(parents=True, exist_ok=True)
            installed_probe.write_bytes(content)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report stale copies without writes"
    )
    args = parser.parse_args()
    changed = sync_bundle(check=args.check)
    if changed and args.check:
        print("Bundled content is stale: " + ", ".join(changed))
        print("Run python sync_plugin_docs.py after editing canonical docs or probe.")
        return 1
    print(
        f"Bundled content {'checked' if args.check else 'synchronized'}: {len(changed)} changes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
