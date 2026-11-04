import unittest

from check_live_contract import inspect_contract


def initialize_result(*, ui_capability=None):
    capabilities = {}
    if ui_capability is not None:
        capabilities["io.modelcontextprotocol/ui"] = ui_capability
    return {
        "result": {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "Gigma Auth: MCP Owner", "version": "1.30.0"},
            "capabilities": capabilities,
        }
    }


def tools_result(*, check_meta=None, include_all=True, annotations=None):
    names = [
        "erp_dialog_check",
        "erp_dialog_start",
        "erp_dialog_status",
        "erp_dialog_connect",
        "erp_dialog_me",
        "erp_dialog_logout",
    ]
    if not include_all:
        names.pop()
    tools = []
    for name in names:
        tool = {"name": name, "description": name}
        if name == "erp_dialog_check":
            tool["annotations"] = annotations or {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            }
            if check_meta is not None:
                tool["_meta"] = check_meta
        tools.append(tool)
    return {"result": {"tools": tools}}


class LiveContractInspectionTests(unittest.TestCase):
    def test_text_only_contract_is_valid_with_safe_check_annotations(self):
        report = inspect_contract(
            initialize_result(), tools_result(), {"result": {"resources": []}}
        )

        self.assertTrue(report.ok)
        self.assertEqual(report.errors, ())
        self.assertEqual(report.warnings, ())

    def test_destructive_check_annotation_breaks_contract(self):
        report = inspect_contract(
            initialize_result(),
            tools_result(
                annotations={
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": False,
                    "openWorldHint": True,
                }
            ),
            {"result": {"resources": []}},
        )

        self.assertFalse(report.ok)
        self.assertTrue(any("destructiveHint" in error for error in report.errors))

    def test_ui_metadata_breaks_text_only_contract(self):
        report = inspect_contract(
            initialize_result(),
            tools_result(check_meta={"ui": {"resourceUri": "ui://gigma/owner-auth/v1.html"}}),
            {"result": {"resources": []}},
        )

        self.assertFalse(report.ok)
        self.assertTrue(any("UI metadata" in error for error in report.errors))

    def test_ui_capability_and_resource_break_text_only_contract(self):
        report = inspect_contract(
            initialize_result(ui_capability={"mimeTypes": ["text/html;profile=mcp-app"]}),
            tools_result(),
            {
                "result": {
                    "resources": [
                        {
                            "uri": "ui://gigma/owner-auth/v1.html",
                            "mimeType": "text/html;profile=mcp-app",
                        }
                    ]
                }
            },
        )

        self.assertFalse(report.ok)
        self.assertGreaterEqual(len(report.errors), 2)

    def test_missing_dialog_tool_breaks_contract(self):
        report = inspect_contract(
            initialize_result(), tools_result(include_all=False), {"result": {}}
        )

        self.assertFalse(report.ok)
        self.assertTrue(any("erp_dialog_logout" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
