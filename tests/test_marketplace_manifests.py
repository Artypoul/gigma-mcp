"""Regression checks for the public marketplace install selector."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from validate_plugin import MARKETPLACE_FILES, ROOT, validate_marketplaces


class MarketplaceManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for relative in (*MARKETPLACE_FILES, "plugins/gigma-mcp/plugin.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def change(self, relative, mutate):
        path = self.root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        mutate(value)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_repository_catalogs_keep_the_public_selector(self):
        validate_marketplaces(self.root)

    def test_renamed_marketplace_is_rejected(self):
        self.change(MARKETPLACE_FILES[0], lambda value: value.update(name="different"))
        with self.assertRaisesRegex(ValueError, "public install selector"):
            validate_marketplaces(self.root)

    def test_renamed_plugin_entry_is_rejected(self):
        self.change(MARKETPLACE_FILES[1], lambda value: value["plugins"][0].update(name="different"))
        with self.assertRaisesRegex(ValueError, "plugin name mismatch"):
            validate_marketplaces(self.root)

    def test_duplicate_plugin_entry_is_rejected(self):
        self.change(MARKETPLACE_FILES[0], lambda value: value["plugins"].append(value["plugins"][0].copy()))
        with self.assertRaisesRegex(ValueError, "exactly one plugin"):
            validate_marketplaces(self.root)

    def test_wrong_source_kind_cannot_pass_with_a_local_looking_path(self):
        self.change(MARKETPLACE_FILES[0], lambda value: value["plugins"][0]["source"].update(source="git"))
        with self.assertRaisesRegex(ValueError, "source must be local"):
            validate_marketplaces(self.root)

    def test_catalog_relative_source_is_rejected(self):
        self.change(MARKETPLACE_FILES[0], lambda value: value["plugins"][0]["source"].update(path="../../plugins/gigma-mcp"))
        with self.assertRaisesRegex(ValueError, "source must be ./plugins/gigma-mcp"):
            validate_marketplaces(self.root)

    def test_blocked_installation_policy_is_rejected(self):
        self.change(MARKETPLACE_FILES[0], lambda value: value["plugins"][0]["policy"].update(installation="BLOCKED"))
        with self.assertRaisesRegex(ValueError, "installation policy mismatch"):
            validate_marketplaces(self.root)

    def test_stale_marketplace_version_is_rejected(self):
        self.change(MARKETPLACE_FILES[2], lambda value: value["plugins"][0].update(version="0.0.0"))
        with self.assertRaisesRegex(ValueError, "entry version mismatch"):
            validate_marketplaces(self.root)

    def test_claude_marketplace_requires_its_owner_metadata(self):
        self.change(MARKETPLACE_FILES[1], lambda value: value.pop("owner"))
        with self.assertRaisesRegex(ValueError, "requires an owner name"):
            validate_marketplaces(self.root)

    def test_missing_source_plugin_is_rejected(self):
        (self.root / "plugins/gigma-mcp/plugin.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing its plugin.json"):
            validate_marketplaces(self.root)

    def test_renamed_source_manifest_is_rejected(self):
        self.change("plugins/gigma-mcp/plugin.json", lambda value: value.update(name="different"))
        with self.assertRaisesRegex(ValueError, "source manifest name mismatch"):
            validate_marketplaces(self.root)


if __name__ == "__main__":
    unittest.main()
