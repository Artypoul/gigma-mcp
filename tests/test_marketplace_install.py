"""Safety and provenance checks; these tests never install a plugin."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import check_marketplace_install as probe


class MarketplaceInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gigma-install-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "runner-home"
        self.home.mkdir()
        self.runner = self.root / "runner-temp"
        self.runner.mkdir()
        self.environment = {"CI": "true", "GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(self.runner),
                            "GITHUB_WORKSPACE": str(self.root / "checkout")}

    def test_ci_and_explicit_guard_are_required_before_any_install(self):
        for flag, environment in ((False, self.environment), (True, {}),
                                  (True, {**self.environment, "GITHUB_ACTIONS": "false"})):
            with self.subTest(flag=flag, environment=environment):
                with self.assertRaises(probe.CheckFailure):
                    probe.require_clean_ci(flag, environment, self.home)

    def test_main_refuses_to_run_installer_without_explicit_guard(self):
        output = io.StringIO()
        with mock.patch.object(probe, "run_json") as command, redirect_stdout(output):
            self.assertEqual(probe.main([]), 1)
        command.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["status"], "failed")

    def test_existing_user_configuration_and_login_are_preserved(self):
        codex = self.home / ".codex"
        codex.mkdir()
        for name in ("config.toml", "auth.json"):
            target = codex / name
            target.write_text("untouched", encoding="utf-8")
            with self.assertRaisesRegex(probe.CheckFailure, "refuses an existing"):
                probe.require_clean_ci(True, self.environment, self.home)
            self.assertEqual(target.read_text(encoding="utf-8"), "untouched")
            target.unlink()
        (codex / "plugins").mkdir()
        with self.assertRaisesRegex(probe.CheckFailure, "refuses an existing"):
            probe.require_clean_ci(True, self.environment, self.home)

    def test_remote_requires_plain_github_url_and_published_commit(self):
        valid = "https://github.com/Artypoul/gigma-mcp"
        commit = "a" * 40
        self.assertEqual(probe.select_source(valid, commit, self.environment), ("git", valid + ".git"))
        for source, revision in ((valid, "main"), (valid, None),
                                 (valid + "?token=secret", commit),
                                 ("https://user:secret@github.com/Artypoul/gigma-mcp", commit),
                                 ("https://example.com/Artypoul/gigma-mcp", commit)):
            with self.subTest(source=source, revision=revision):
                with self.assertRaises(probe.CheckFailure):
                    probe.select_source(source, revision, self.environment)

    def test_local_mode_stays_in_checkout_and_does_not_accept_ref(self):
        checkout = Path(self.environment["GITHUB_WORKSPACE"])
        checkout.mkdir()
        self.assertEqual(probe.select_source(str(checkout), None, self.environment), ("local", str(checkout)))
        with self.assertRaises(probe.CheckFailure):
            probe.select_source(str(checkout), "a" * 40, self.environment)
        with self.assertRaises(probe.CheckFailure):
            probe.select_source(str(self.home), None, self.environment)

    def test_returned_cache_path_cannot_escape_runner_root(self):
        with self.assertRaises(probe.CheckFailure):
            probe.returned_directory(str(self.home), (self.runner,))
        link = self.runner / "outside"
        link.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(probe.CheckFailure):
            probe.returned_directory(str(link), (self.runner,))

    def test_provenance_mismatch_is_an_error_and_absence_is_explicit(self):
        source = "https://github.com/Artypoul/gigma-mcp.git"
        self.assertFalse(probe.check_provenance({}, "git", source))
        self.assertTrue(probe.check_provenance({"marketplaceSource": {"sourceType": "git", "source": source}}, "git", source))
        with self.assertRaises(probe.CheckFailure):
            probe.check_provenance({"marketplaceSource": {"sourceType": "local", "source": source}}, "git", source)

    def test_cache_components_require_expected_version_and_mcp_contract(self):
        original = probe.ROOT / probe.PACKAGE_RELATIVE
        package = self.runner / "package"
        shutil.copytree(original, package)
        version = json.loads((package / "plugin.json").read_text(encoding="utf-8"))["version"]
        contents = probe.inspect_package(package, version)
        self.assertEqual(len(contents), 8)
        with self.assertRaises(probe.CheckFailure):
            probe.inspect_package(package, "999.0.0")
        mcp = json.loads((package / "mcp.json").read_text(encoding="utf-8"))
        mcp["mcpServers"]["other"] = mcp["mcpServers"]["gigma"]
        (package / "mcp.json").write_text(json.dumps(mcp), encoding="utf-8")
        with self.assertRaisesRegex(probe.CheckFailure, "exactly the canonical"):
            probe.inspect_package(package, version)

    def test_process_errors_do_not_expose_raw_output(self):
        with self.assertRaises(probe.CheckFailure) as caught:
            probe.run_bounded([sys.executable, "-c", "import sys; print('secret-value', file=sys.stderr); sys.exit(1)"],
                              cwd=self.runner, timeout=2, stage="test command")
        self.assertNotIn("secret-value", str(caught.exception))

    def test_process_timeout_is_bounded(self):
        with self.assertRaisesRegex(probe.CheckFailure, "timed out"):
            probe.run_bounded([sys.executable, "-c", "import time; time.sleep(10)"],
                              cwd=self.runner, timeout=0.05, stage="test command")


if __name__ == "__main__":
    unittest.main()
