import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins/gigma-mcp"


class PackagedDocumentationTests(unittest.TestCase):
    def test_installed_probe_runs_help_and_inspects_contract_without_repository(self):
        fixture = json.loads(
            (ROOT / "tests/fixtures/owner_mcp_contract.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            installed = Path(directory) / "installed-plugin"
            shutil.copytree(PACKAGE, installed)
            checker = installed / "check_live_contract.py"
            self.assertTrue(
                checker.is_file(), "the installed instructions need a runnable checker"
            )
            spec = importlib.util.spec_from_file_location(
                "isolated_gigma_probe", checker
            )
            module = importlib.util.module_from_spec(spec)
            without_repository = [
                p for p in sys.path if Path(p or ".").resolve() != ROOT
            ]
            with (
                patch.dict(sys.modules, {spec.name: module}),
                patch.object(sys, "path", without_repository),
            ):
                spec.loader.exec_module(module)
                report = module.inspect_contract(
                    fixture["initialize"],
                    fixture["tools_list"],
                    fixture["resources_list"],
                )
                self.assertTrue(report.ok, report.errors)
                help_output = io.StringIO()
                with (
                    patch.object(sys, "argv", [str(checker), "--help"]),
                    contextlib.redirect_stdout(help_output),
                ):
                    with self.assertRaises(SystemExit) as result:
                        module.main()
                self.assertEqual(result.exception.code, 0)
                self.assertIn("--timeout", help_output.getvalue())

    def test_installed_subtree_has_no_repository_documentation_dependency(self):
        from validate_plugin import validate_packaged_links

        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            installed = Path(directory) / "installed-plugin"
            shutil.copytree(PACKAGE, installed)
            validate_packaged_links(installed)
            self.assertTrue((installed / "docs/mcp-client-setup.md").is_file())

    def test_missing_packaged_document_is_rejected(self):
        from validate_plugin import validate_packaged_links

        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            installed = Path(directory) / "installed-plugin"
            shutil.copytree(PACKAGE, installed)
            (installed / "docs/mcp-client-setup.md").unlink()
            with self.assertRaisesRegex(ValueError, "missing.*mcp-client-setup"):
                validate_packaged_links(installed)

    def test_links_cannot_escape_installed_plugin_even_if_target_exists(self):
        from validate_plugin import validate_packaged_links

        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            parent = Path(directory)
            installed = parent / "installed-plugin"
            installed.mkdir()
            (parent / "outside.md").write_text("outside", encoding="utf-8")
            (installed / "README.md").write_text(
                "[bad](../outside.md)", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "escapes"):
                validate_packaged_links(installed)

    def test_bundled_docs_match_the_canonical_sources(self):
        from sync_plugin_docs import sync_bundle

        self.assertEqual(sync_bundle(check=True), [])

    def test_stale_bundled_probe_is_detected_without_overwriting_it(self):
        from sync_plugin_docs import sync_bundle

        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            parent = Path(directory)
            (parent / "docs").mkdir()
            (parent / "check_live_contract.py").write_text(
                "canonical", encoding="utf-8"
            )
            package = parent / "plugins/gigma-mcp"
            package.mkdir(parents=True)
            target = package / "check_live_contract.py"
            target.write_text("stale", encoding="utf-8")
            self.assertEqual(
                sync_bundle(root=parent, check=True), ["check_live_contract.py"]
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "stale")

    def test_stale_bundled_doc_is_detected_without_overwriting_it(self):
        from sync_plugin_docs import sync_docs

        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".package-test-"
        ) as directory:
            parent = Path(directory)
            sources = parent / "docs"
            bundled = parent / "plugin/docs"
            sources.mkdir()
            bundled.mkdir(parents=True)
            (sources / "guide.md").write_text("canonical", encoding="utf-8")
            target = bundled / "guide.md"
            target.write_text("stale", encoding="utf-8")
            self.assertEqual(
                sync_docs(source=sources, destination=bundled, check=True), ["guide.md"]
            )
            self.assertEqual(target.read_text(encoding="utf-8"), "stale")


if __name__ == "__main__":
    unittest.main()
