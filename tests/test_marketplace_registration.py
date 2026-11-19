import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import check_client_registration as registration


class RepositoryMarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        self.package = self.repository / registration.PACKAGE_RELATIVE
        self.package.parent.mkdir(parents=True)
        shutil.copytree(registration.ROOT / registration.PACKAGE_RELATIVE, self.package)
        self.marketplace = self.repository / registration.MARKETPLACE_RELATIVE
        self.marketplace.parent.mkdir(parents=True)
        self.marketplace.write_bytes(
            (registration.ROOT / registration.MARKETPLACE_RELATIVE).read_bytes()
        )
        self.destination = self.directory / "probe"
        self.version = json.loads((self.package / "plugin.json").read_text())["version"]

    def catalog(self):
        return json.loads(self.marketplace.read_bytes())

    def write_catalog(self, catalog):
        self.marketplace.write_text(json.dumps(catalog, indent=3) + "\n", encoding="utf-8")

    def prepare(self, *, regression=False):
        return registration.prepare_repository_marketplace(
            self.repository, self.destination, regression=regression,
        )

    def response(self, *, version=None):
        summary = {"name": registration.PLUGIN_NAME}
        if version is not None:
            summary["version"] = version
        return {"result": {"plugin": {
            "summary": summary,
            "mcpServers": ["gigma"],
            "skills": [{"name": name} for name in sorted(registration.EXPECTED_SKILLS)],
        }}}

    def test_real_catalog_bytes_and_declared_path_survive_without_unrelated_files(self):
        catalog = self.catalog()
        catalog["interface"] = {"displayName": "Real repository marketplace"}
        catalog["plugins"][0]["description"] = "Must reach the loader unchanged."
        self.write_catalog(catalog)
        (self.repository / "unrelated-local.txt").write_text("Do not copy this file")
        (self.repository / ".git").mkdir()
        (self.repository / ".git/config").write_text("Do not copy repository metadata")

        copied_marketplace, version = self.prepare()

        self.assertEqual(version, self.version)
        self.assertEqual(copied_marketplace, self.destination / registration.MARKETPLACE_RELATIVE)
        self.assertEqual(copied_marketplace.read_bytes(), self.marketplace.read_bytes())
        copied_package = self.destination / registration.PACKAGE_RELATIVE
        for name in ("plugin.json", "mcp.json"):
            self.assertEqual((copied_package / name).read_bytes(), (self.package / name).read_bytes())
        self.assertFalse((self.destination / "unrelated-local.txt").exists())
        self.assertFalse((self.destination / ".git").exists())
        self.assertFalse((self.destination / registration.PLUGIN_NAME).exists())

    def test_missing_real_marketplace_cannot_fall_back_to_synthetic_catalog(self):
        self.marketplace.unlink()
        with self.assertRaisesRegex(registration.CheckFailure, "missing .agents/plugins/marketplace.json"):
            self.prepare()

    def test_invalid_catalog_and_missing_or_duplicate_selected_entry_fail(self):
        original = self.catalog()
        for broken in (
            [],
            {**original, "name": "different-marketplace"},
            {**original, "plugins": {}},
            {**original, "plugins": [None]},
            {**original, "plugins": []},
            {**original, "plugins": original["plugins"] * 2},
        ):
            with self.subTest(catalog=broken):
                self.write_catalog(broken)
                with self.assertRaises(registration.CheckFailure):
                    self.prepare()
        self.marketplace.write_text("{not-json", encoding="utf-8")
        with self.assertRaisesRegex(registration.CheckFailure, "not valid JSON"):
            self.prepare()

    def test_absent_remote_or_malformed_source_cannot_hide_broken_repository_entry(self):
        original = self.catalog()
        for source in (None, {}, "./plugins/gigma-mcp", {"source": "git", "path": "./plugins/gigma-mcp"},
                       {"source": "local"}, {"source": "local", "path": []}):
            with self.subTest(source=source):
                catalog = copy.deepcopy(original)
                catalog["plugins"][0]["source"] = source
                self.write_catalog(catalog)
                with self.assertRaises(registration.CheckFailure):
                    self.prepare()

    def test_unsafe_or_wrong_source_paths_fail_before_copying(self):
        original = self.catalog()
        for path in ("../gigma-mcp", "/tmp/gigma-mcp", "plugins/../gigma-mcp",
                     "C:\\plugins\\gigma-mcp", "plugins\\gigma-mcp", "", "\x00",
                     "plugins/gigma-mcp-other", "."):
            with self.subTest(path=path):
                catalog = copy.deepcopy(original)
                catalog["plugins"][0]["source"]["path"] = path
                self.write_catalog(catalog)
                with self.assertRaises(registration.CheckFailure):
                    self.prepare()
                self.assertFalse(self.destination.exists())

    def test_missing_package_and_mismatched_package_identity_fail(self):
        manifest = self.package / "plugin.json"
        data = json.loads(manifest.read_bytes())
        data["name"] = "different-plugin"
        manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(registration.CheckFailure, "identity do not match"):
            self.prepare()
        shutil.rmtree(self.package)
        with self.assertRaisesRegex(registration.CheckFailure, "package is missing"):
            self.prepare()

    def test_symlinked_source_directory_is_rejected(self):
        moved = self.directory / "outside-package"
        self.package.rename(moved)
        self.package.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(registration.CheckFailure, "symbolic links"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_symlinked_marketplace_directory_is_rejected(self):
        moved = self.directory / "outside-catalog"
        self.marketplace.parent.rename(moved)
        self.marketplace.parent.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(registration.CheckFailure, "symbolic links"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_package_symlink_does_not_leak_unrelated_files(self):
        outside = self.directory / "private.txt"
        outside.write_text("Do not read or copy")
        (self.package / "unrelated.txt").symlink_to(outside)
        with self.assertRaisesRegex(registration.CheckFailure, "symbolic links"):
            self.prepare()
        self.assertFalse((self.destination / registration.PACKAGE_RELATIVE).exists())

    def test_regression_changes_only_temporary_mcp_config_not_real_catalog_or_source(self):
        original_mcp = (self.package / "mcp.json").read_bytes()
        copied_marketplace, _ = self.prepare(regression=True)
        copied_config = json.loads((self.destination / registration.PACKAGE_RELATIVE / "mcp.json").read_bytes())
        self.assertIn("extensions", copied_config["mcpServers"]["gigma"])
        self.assertEqual((self.package / "mcp.json").read_bytes(), original_mcp)
        self.assertEqual(copied_marketplace.read_bytes(), self.marketplace.read_bytes())

    def test_loader_version_is_verified_when_exposed_and_optional_for_older_clients(self):
        for version in (None, self.version):
            result = registration.check_result(
                self.response(version=version), [], regression=False, expected_version=self.version,
            )
            self.assertEqual(result["status"], "passed")
        with self.assertRaisesRegex(registration.CheckFailure, "version does not match"):
            registration.check_result(
                self.response(version="0.0.0-stale"), [], regression=False, expected_version=self.version,
            )

    def test_repository_cli_sends_actual_catalog_to_loader_and_never_synthesizes_it(self):
        expected = self.marketplace.read_bytes()

        def load_real_catalog(codex, marketplace, runtime, timeout):
            self.assertEqual(marketplace.read_bytes(), expected)
            self.assertTrue((marketplace.parents[2] / registration.PACKAGE_RELATIVE / "plugin.json").is_file())
            return self.response(version=self.version), []

        with mock.patch.object(sys, "argv", ["check_client_registration.py", "--marketplace-root", str(self.repository)]), \
             mock.patch.object(registration.shutil, "which", return_value="codex"), \
             mock.patch.object(registration.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"codex-cli 0.170.0\n")), \
             mock.patch.object(registration, "prepare_marketplace", side_effect=AssertionError("Must not synthesize catalog")), \
             mock.patch.object(registration, "read_with_codex", side_effect=load_real_catalog) as reader, \
             mock.patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(registration.main(), 0)
            reader.assert_called_once()
            self.assertIn('"source": "repository"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
