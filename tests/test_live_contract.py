import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from check_live_contract import PROTOCOL_VERSION, inspect_contract, run_live_check

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/owner_mcp_contract.json").read_text(
        encoding="utf-8"
    )
)


def contract():
    return tuple(
        copy.deepcopy(FIXTURE[key])
        for key in ("initialize", "tools_list", "resources_list")
    )


def tool(tools, name):
    return next(item for item in tools["result"]["tools"] if item["name"] == name)


class LiveContractInspectionTests(unittest.TestCase):
    def assert_invalid(self, initialize, tools, resources, marker):
        report = inspect_contract(initialize, tools, resources)
        self.assertFalse(report.ok, report)
        self.assertTrue(any(marker in error for error in report.errors), report.errors)

    def test_actual_backend_metadata_fixture_is_compatible(self):
        report = inspect_contract(*contract())
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.warnings, ())

    def test_live_probe_only_discovers_metadata_and_never_calls_a_tool(self):
        initialize, tools, resources = contract()
        with patch(
            "check_live_contract.post_json",
            side_effect=[(200, initialize), (202, {}), (200, tools), (200, resources)],
        ) as post:
            self.assertTrue(run_live_check("https://example.invalid/mcp/", 1).ok)
        payloads = [call.args[1] for call in post.call_args_list]
        self.assertEqual(
            [payload["method"] for payload in payloads],
            ["initialize", "notifications/initialized", "tools/list", "resources/list"],
        )
        self.assertEqual(payloads[0]["params"]["protocolVersion"], PROTOCOL_VERSION)

    def test_each_native_tool_is_required_including_recovery(self):
        names = [item["name"] for item in FIXTURE["tools_list"]["result"]["tools"]]
        for name in (item for item in names if item.startswith("erp_dialog_")):
            with self.subTest(name=name):
                initialize, tools, resources = contract()
                tools["result"]["tools"] = [
                    item for item in tools["result"]["tools"] if item["name"] != name
                ]
                self.assert_invalid(initialize, tools, resources, name)

    def test_missing_or_empty_input_schema_is_rejected(self):
        for schema in (
            None,
            {},
            {"type": "object", "properties": {}, "additionalProperties": False},
        ):
            with self.subTest(schema=schema):
                initialize, tools, resources = contract()
                tool(tools, "erp_dialog_check")["inputSchema"] = schema
                self.assert_invalid(initialize, tools, resources, "erp_dialog_check")

    def test_new_required_credential_breaks_native_compatibility(self):
        initialize, tools, resources = contract()
        schema = tool(tools, "erp_dialog_check")["inputSchema"]
        schema["properties"]["access_token"] = {"type": "string"}
        schema["required"].append("access_token")
        self.assert_invalid(initialize, tools, resources, "required")

    def test_required_field_cannot_be_optional_or_project_name_required_for_login(self):
        for name, field, remove in (
            ("erp_dialog_check", "phone", True),
            ("erp_dialog_start", "project_name", False),
        ):
            with self.subTest(name=name):
                initialize, tools, resources = contract()
                required = tool(tools, name)["inputSchema"]["required"]
                required.remove(field) if remove else required.append(field)
                self.assert_invalid(initialize, tools, resources, "required")

    def test_native_type_pattern_bounds_and_extra_constraints_are_checked(self):
        for field, key, value in (
            ("phone", "type", "boolean"),
            ("phone", "maxLength", 11),
            ("idempotency_key", "pattern", "^short$"),
            ("idempotency_key", "enum", ["one-fixed-key"]),
        ):
            with self.subTest(field=field, key=key):
                initialize, tools, resources = contract()
                tool(tools, "erp_dialog_check")["inputSchema"]["properties"][field][
                    key
                ] = value
                self.assert_invalid(initialize, tools, resources, field)

    def test_open_or_constrained_native_object_is_rejected(self):
        for key, value in (("additionalProperties", True), ("maxProperties", 0)):
            with self.subTest(key=key):
                initialize, tools, resources = contract()
                tool(tools, "erp_dialog_check")["inputSchema"][key] = value
                self.assert_invalid(initialize, tools, resources, "erp_dialog_check")

    def test_optional_addition_and_documentation_changes_are_compatible(self):
        initialize, tools, resources = contract()
        schema = tool(tools, "erp_dialog_check")["inputSchema"]
        schema["title"] = "Harmless title change"
        schema["properties"]["phone"]["description"] = "Harmless description change"
        schema["properties"]["optional_hint"] = {"type": "string"}
        self.assertTrue(inspect_contract(initialize, tools, resources).ok)

    def test_every_business_tool_requires_the_native_session_capability(self):
        for name in ("erp_list_applications", "erp_get_application"):
            for change in ("missing", "optional", "wrong_pattern"):
                with self.subTest(name=name, change=change):
                    initialize, tools, resources = contract()
                    schema = tool(tools, name)["inputSchema"]
                    if change == "missing":
                        schema["properties"].pop("session_capability")
                    elif change == "optional":
                        schema["required"].remove("session_capability")
                    else:
                        schema["properties"]["session_capability"]["pattern"] = ".*"
                    self.assert_invalid(initialize, tools, resources, name)

    def test_additional_protected_business_tools_are_allowed(self):
        initialize, tools, resources = contract()
        extra = copy.deepcopy(tool(tools, "erp_get_application"))
        extra["name"] = "erp_get_plan_revision"
        tools["result"]["tools"].append(extra)
        self.assertTrue(inspect_contract(initialize, tools, resources).ok)

    def test_business_root_constraints_cannot_hide_required_credentials(self):
        for key, value in (
            ("allOf", [{"required": ["access_token"]}]),
            ("if", {"properties": {"name": {"type": "string"}}}),
            ("maxProperties", 0),
        ):
            with self.subTest(key=key):
                initialize, tools, resources = contract()
                tool(tools, "erp_get_application")["inputSchema"][key] = value
                self.assert_invalid(initialize, tools, resources, "object constraints")

    def test_native_only_catalog_is_not_a_business_contract(self):
        initialize, tools, resources = contract()
        tools["result"]["tools"] = [
            item
            for item in tools["result"]["tools"]
            if item["name"].startswith("erp_dialog_")
        ]
        self.assert_invalid(initialize, tools, resources, "business")

    def test_duplicate_tool_names_are_rejected(self):
        initialize, tools, resources = contract()
        tools["result"]["tools"].append(copy.deepcopy(tool(tools, "erp_dialog_check")))
        self.assert_invalid(initialize, tools, resources, "duplicate")

    def test_unread_catalog_pages_are_not_reported_as_complete(self):
        for target in ("tools", "resources"):
            with self.subTest(target=target):
                initialize, tools, resources = contract()
                (tools if target == "tools" else resources)["result"]["nextCursor"] = (
                    "next-page"
                )
                self.assert_invalid(initialize, tools, resources, "pagination")

    def test_identity_version_protocol_and_tools_capability_are_checked(self):
        for field, value, marker in (
            ("name", "different-server", "identity"),
            ("version", "", "version"),
            ("protocolVersion", "1900-01-01", "protocol"),
            ("capabilities", {}, "tools capability"),
        ):
            with self.subTest(field=field):
                initialize, tools, resources = contract()
                result = initialize["result"]
                (result["serverInfo"] if field in ("name", "version") else result)[
                    field
                ] = value
                self.assert_invalid(initialize, tools, resources, marker)

    def test_destructive_check_annotation_breaks_contract(self):
        initialize, tools, resources = contract()
        tool(tools, "erp_dialog_check")["annotations"]["destructiveHint"] = True
        self.assert_invalid(initialize, tools, resources, "destructiveHint")

    def test_ui_metadata_breaks_text_only_contract(self):
        initialize, tools, resources = contract()
        tool(tools, "erp_dialog_check")["_meta"] = {
            "ui": {"resourceUri": "ui://gigma/owner-auth/v1.html"}
        }
        self.assert_invalid(initialize, tools, resources, "UI metadata")

    def test_ui_capability_and_resource_break_text_only_contract(self):
        initialize, tools, resources = contract()
        initialize["result"]["capabilities"]["io.modelcontextprotocol/ui"] = {}
        resources["result"]["resources"] = [
            {
                "uri": "ui://gigma/owner-auth/v1.html",
                "mimeType": "text/html;profile=mcp-app",
            }
        ]
        report = inspect_contract(initialize, tools, resources)
        self.assertFalse(report.ok)
        self.assertGreaterEqual(len(report.errors), 2)


if __name__ == "__main__":
    unittest.main()
