import copy
import unittest

from validate_plugin import PACKAGE, load, validate_portable_metadata


class PortableMetadataTests(unittest.TestCase):
    def setUp(self):
        self.portable = load(PACKAGE / "plugin.json")
        self.codex = load(PACKAGE / ".codex-plugin/plugin.json")

    def test_complete_portable_metadata_matches_compatibility_overlay(self):
        validate_portable_metadata(self.portable, self.codex)

    def test_partial_openai_override_cannot_silently_drop_legacy_settings(self):
        for field in ("interface", "onboardingSkill"):
            with self.subTest(field=field):
                portable = copy.deepcopy(self.portable)
                del portable["extensions"]["com.openai"][field]
                with self.assertRaises(ValueError):
                    validate_portable_metadata(portable, self.codex)

    def test_unrecognized_portable_schema_and_legacy_fields_are_rejected(self):
        for field, value in (("$schema", "legacy"), ("mcpServers", "./mcp.json")):
            with self.subTest(field=field):
                portable = copy.deepcopy(self.portable)
                portable[field] = value
                with self.assertRaises(ValueError):
                    validate_portable_metadata(portable, self.codex)

    def test_import_limits_and_prompt_types_are_validated(self):
        for field, value in (
            ("shortDescription", "x" * 31),
            ("defaultPrompt", []),
            ("defaultPrompt", ["one", "two", "three", "four"]),
            ("defaultPrompt", [None]),
            ("capabilities", "Read"),
            ("displayName", " "),
        ):
            with self.subTest(field=field, value=value):
                portable = copy.deepcopy(self.portable)
                codex = copy.deepcopy(self.codex)
                portable["extensions"]["com.openai"]["interface"][field] = value
                codex["interface"][field] = value
                with self.assertRaises(ValueError):
                    validate_portable_metadata(portable, codex)

    def test_prompt_value_type_and_order_remain_in_sync(self):
        codex = copy.deepcopy(self.codex)
        codex["interface"]["defaultPrompt"] = "A changed prompt"
        with self.assertRaisesRegex(ValueError, "metadata must match"):
            validate_portable_metadata(self.portable, codex)


if __name__ == "__main__":
    unittest.main()
