import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ChatGPTPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gigma-archive-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        shutil.copytree(
            ROOT,
            self.repository,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "*.pyc", "dist", ".venv",
                ".pytest_cache", ".package-test-*",
            ),
        )
        self.package = self.repository / "plugins" / "gigma-mcp"
        self.output = self.directory / "gigma.zip"

    def run_builder(self, *, output=True, app_id=None):
        command = [sys.executable, str(self.repository / "build_chatgpt_package.py")]
        if output:
            command.extend(["--output", str(self.output)])
        if app_id is not None:
            command.extend(["--chatgpt-app-id", app_id])
        return subprocess.run(
            command, cwd=self.directory, text=True, capture_output=True, timeout=15
        )

    def build(self):
        result = self.run_builder()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.output.read_bytes()

    def test_archive_is_one_self_contained_portable_plugin_and_preserves_bytes(self):
        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        )
        assets = self.package / "assets"
        assets.mkdir(exist_ok=True)
        (assets / "logo.png").write_bytes(image)
        (self.package / ".env").write_text("not for distribution", encoding="utf-8")
        (self.package / "unrelated.txt").write_text("not a component", encoding="utf-8")
        (self.package / "docs/.DS_Store").write_bytes(b"desktop metadata")
        cache = self.package / "skills/__pycache__"
        cache.mkdir()
        (cache / "local.pyc").write_bytes(b"compiled cache")

        result = self.run_builder(output=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = json.loads((self.package / "plugin.json").read_text(encoding="utf-8"))
        output = self.repository / "dist" / f"gigma-mcp-{manifest['version']}-chatgpt.zip"
        with zipfile.ZipFile(output) as archive:
            names = archive.namelist()
            self.assertEqual(archive.testzip(), None)
            self.assertEqual({name.split("/")[0] for name in names}, {"gigma-mcp"})
            for relative in (
                "plugin.json", "mcp.json", "LICENSE", "README.md",
                "check_live_contract.py", "docs/mcp-client-setup.md",
            ):
                self.assertEqual(
                    archive.read(f"gigma-mcp/{relative}"),
                    (self.package / relative).read_bytes(),
                )
            skills = list((self.package / "skills").glob("*/SKILL.md"))
            self.assertGreaterEqual(len(skills), 6)
            for skill in skills:
                self.assertIn(f"gigma-mcp/{skill.relative_to(self.package).as_posix()}", names)
            self.assertEqual(archive.read("gigma-mcp/assets/logo.png"), image)
            self.assertFalse(any("marketplace" in name for name in names))
            self.assertFalse(any("/." in name or "__pycache__" in name for name in names))
            self.assertNotIn("gigma-mcp/unrelated.txt", names)
            self.assertNotIn("gigma-mcp/.codex-plugin/plugin.json", names)
            self.assertNotIn("gigma-mcp/.claude-plugin/plugin.json", names)
            self.assertNotIn("gigma-mcp/.cursor-plugin/plugin.json", names)

    def test_bound_archive_has_app_binding_and_preserves_portable_archive_and_source(self):
        result = self.run_builder(output=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source_manifest = (self.package / "plugin.json").read_bytes()
        source_mcp = (self.package / "mcp.json").read_bytes()
        version = json.loads(source_manifest)["version"]
        portable_path = self.repository / "dist" / f"gigma-mcp-{version}-chatgpt.zip"
        portable = portable_path.read_bytes()
        app_id = "asdk_app_FAKE_TEST_ONLY_123"
        result = self.run_builder(output=False, app_id=app_id)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bound = self.repository / "dist" / f"gigma-mcp-{version}-chatgpt-app.zip"
        with zipfile.ZipFile(bound) as archive, zipfile.ZipFile(portable_path) as default:
            self.assertEqual(archive.testzip(), None)
            self.assertNotIn("gigma-mcp/mcp.json", archive.namelist())
            manifest = json.loads(archive.read("gigma-mcp/plugin.json"))
            source = json.loads(source_manifest)
            source["extensions"]["com.openai"]["apps"] = "./.app.json"
            self.assertEqual(manifest, source)
            self.assertEqual(json.loads(archive.read("gigma-mcp/.app.json")),
                             {"apps": {"gigma": {"id": app_id, "required": True}}})
            for name in set(default.namelist()) - {"gigma-mcp/plugin.json", "gigma-mcp/mcp.json"}:
                self.assertEqual(archive.read(name), default.read(name))
            self.assertEqual(set(archive.namelist()),
                             (set(default.namelist()) - {"gigma-mcp/mcp.json"}) | {"gigma-mcp/.app.json"})
        first = bound.read_bytes()
        result = self.run_builder(output=False, app_id=app_id)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(bound.read_bytes(), first)
        self.assertEqual(portable_path.read_bytes(), portable)
        self.assertEqual((self.package / "plugin.json").read_bytes(), source_manifest)
        self.assertEqual((self.package / "mcp.json").read_bytes(), source_mcp)
        self.assertFalse((self.package / ".app.json").exists())

    def test_app_id_prefixes_are_accepted(self):
        for app_id in ("asdk_app_FAKE123", "connector_FAKE123", "templated_apps_FAKE123"):
            with self.subTest(app_id=app_id):
                result = self.run_builder(app_id=app_id)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with zipfile.ZipFile(self.output) as archive:
                    self.assertEqual(json.loads(archive.read("gigma-mcp/.app.json"))["apps"]["gigma"]["id"], app_id)

    def test_invalid_app_ids_do_not_replace_existing_output(self):
        original = self.build()
        for app_id in ("", "asdk_app_", "connector_", "templated_apps_", "plugin_fake",
                       "https://example.com", "asdk_app_-fake", "asdk_app__fake",
                       "connector_-fake", "templated_apps__fake",
                       "asdk_app_fake value", "asdk_app_fake/evil",
                       "asdk_app_fake\n"):
            with self.subTest(app_id=app_id):
                result = self.run_builder(app_id=app_id)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("App ID", result.stdout)
                self.assertEqual(self.output.read_bytes(), original)

    def test_rebuilding_after_source_time_and_mode_changes_is_identical(self):
        original = self.build()
        for path in self.package.rglob("*"):
            if path.is_file():
                os.utime(path, (1_900_000_000, 1_900_000_000))
                path.chmod(0o600)
        self.assertEqual(self.build(), original)

    def test_selected_symlink_file_or_directory_is_rejected_without_reading_target(self):
        assets = self.package / "assets"
        assets.mkdir(exist_ok=True)
        outside = self.directory / "outside.txt"
        outside.write_text("outside package", encoding="utf-8")
        link = assets / "link.txt"
        for target in (outside, self.directory):
            with self.subTest(target=target):
                link.symlink_to(target, target_is_directory=target.is_dir())
                result = self.run_builder()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("symlinks are not allowed", result.stdout)
                self.assertFalse(self.output.exists())
                link.unlink()

    def test_symlinked_plugins_directory_is_rejected(self):
        detached = self.directory / "detached-plugins"
        (self.repository / "plugins").rename(detached)
        (self.repository / "plugins").symlink_to(detached, target_is_directory=True)
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin directory must not be a symlink", result.stdout)
        self.assertFalse(self.output.exists())

    def test_archive_output_inside_package_is_rejected(self):
        self.output = self.package / "assets" / "self.zip"
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the plugin directory", result.stdout)
        self.assertFalse(self.output.exists())

    def test_invalid_manifest_does_not_replace_an_existing_archive(self):
        original = self.build()
        (self.package / "plugin.json").write_text("{invalid JSON", encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), original)

    def test_auth_extension_that_hides_mcp_in_codex_cannot_be_released(self):
        original = self.build()
        path = self.package / "mcp.json"
        mcp = json.loads(path.read_text(encoding="utf-8"))
        mcp["mcpServers"]["gigma"]["extensions"] = {
            "com.openai": {"auth": {"type": "none"}}
        }
        path.write_text(json.dumps(mcp), encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported fields such as extensions", result.stdout)
        self.assertEqual(self.output.read_bytes(), original)

    def test_app_binding_cannot_be_silently_omitted_from_portable_remote_archive(self):
        original = self.build()
        path = self.package / "plugin.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["extensions"]["com.openai"]["apps"] = "./.app.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("app-bound plugins require a separate archive", result.stdout)
        self.assertEqual(self.output.read_bytes(), original)

    def test_stale_bundled_document_does_not_replace_an_existing_archive(self):
        original = self.build()
        canonical = self.repository / "docs/mcp-client-setup.md"
        canonical.write_text(canonical.read_text(encoding="utf-8") + "\nNew guidance.\n", encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bundled content is stale", result.stdout.lower())
        self.assertEqual(self.output.read_bytes(), original)

    def test_credential_value_in_an_additional_skill_file_is_rejected(self):
        references = self.package / "skills/gigma-owner-auth/references"
        references.mkdir(exist_ok=True)
        (references / "settings.json").write_text(
            json.dumps({"access_token": "do-not-package-this-value"}), encoding="utf-8"
        )
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("secret-like value must not be packaged", result.stdout)
        self.assertFalse(self.output.exists())

    def test_a_link_to_an_excluded_file_cannot_produce_a_broken_archive(self):
        hidden = self.package / "skills/gigma-owner-auth/.local.md"
        hidden.write_text("not portable", encoding="utf-8")
        skill = self.package / "skills/gigma-owner-auth/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\n[local](.local.md)\n", encoding="utf-8")
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing packaged link", result.stdout)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
