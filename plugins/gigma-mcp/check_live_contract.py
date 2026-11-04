#!/usr/bin/env python3
"""Read-only check for the deployed text-only Gigma owner MCP contract."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_URL = "https://api.auth.gigma.ru/mcp/owner/"
SERVER_NAME = "Gigma Auth: MCP Owner"
PROTOCOL_VERSION = "2025-06-18"
NATIVE_DIALOG_TOOLS = (
    "erp_dialog_check",
    "erp_dialog_start",
    "erp_dialog_status",
    "erp_dialog_reconcile",
    "erp_dialog_connect",
    "erp_dialog_cancel",
    "erp_dialog_me",
    "erp_dialog_logout",
)
_DIALOG_CAPABILITY = {"type": "string", "pattern": r"^mcp_d_a_[a-f0-9]{64}$"}
_SESSION_CAPABILITY = {"type": "string", "pattern": r"^mcp_d_s_[a-f0-9]{64}$"}
_CHECK_PROPERTIES = {
    "phone": {"type": "string", "minLength": 10, "maxLength": 40},
    "idempotency_key": {
        "type": "string",
        "minLength": 32,
        "maxLength": 128,
        "pattern": r"^[A-Za-z0-9_-]{32,128}$",
    },
}
_START_PROPERTIES = {
    "dialog_capability": _DIALOG_CAPABILITY,
    "action": {"type": "string", "pattern": r"^(login|register)$"},
    "project_name": {
        "anyOf": [{"type": "string", "maxLength": 150}, {"type": "null"}],
        "default": None,
    },
    "consent": {"type": "boolean"},
}
_SCHEMA_ANNOTATIONS = {"title", "description", "examples", "$comment"}
UI_MARKERS = (
    "io.modelcontextprotocol/ui",
    "resourceUri",
    "text/html;profile=mcp-app",
    "ui/resource",
    "ui://",
)


def _schema_contract(value: Any) -> Any:
    """Ignore documentation, retaining every validation/default keyword.

    This is a conservative compatibility comparison, not a general JSON Schema
    validator. A changed native constraint requires an explicit package review.
    """
    if isinstance(value, dict):
        return {
            key: _schema_contract(item)
            for key, item in value.items()
            if key not in _SCHEMA_ANNOTATIONS
        }
    if isinstance(value, list):
        return [_schema_contract(item) for item in value]
    return value


def _inspect_input_schema(tool: dict[str, Any], errors: list[str]) -> None:
    name = tool["name"]
    schema = tool.get("inputSchema")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        errors.append(f"{name} requires an object inputSchema")
        return
    properties = schema.get("properties")
    required = schema.get("required", [])
    if (
        not isinstance(properties, dict)
        or not isinstance(required, list)
        or any(not isinstance(item, str) for item in required)
    ):
        errors.append(f"{name} has malformed properties/required inputSchema")
        return
    if schema.get("additionalProperties") is not False:
        errors.append(f"{name} inputSchema must reject additional properties")
    if len(required) != len(set(required)) or not set(required) <= properties.keys():
        errors.append(f"{name} has invalid required input fields")
    allowed_keys = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "$defs",
        "$schema",
    }
    if set(schema) - allowed_keys - _SCHEMA_ANNOTATIONS:
        errors.append(f"{name} inputSchema has unreviewed object constraints")
    if name not in NATIVE_DIALOG_TOOLS:
        if (
            "session_capability" not in required
            or _schema_contract(properties.get("session_capability"))
            != _SESSION_CAPABILITY
        ):
            errors.append(
                f"{name} business input requires a bounded session_capability"
            )
        return

    if name == "erp_dialog_check":
        expected = _CHECK_PROPERTIES
        expected_required = set(expected)
    elif name == "erp_dialog_start":
        expected = _START_PROPERTIES
        expected_required = {"dialog_capability", "action", "consent"}
    elif name in {"erp_dialog_me", "erp_dialog_logout"}:
        expected = {"session_capability": _SESSION_CAPABILITY}
        expected_required = set(expected)
    else:
        expected = {"dialog_capability": _DIALOG_CAPABILITY}
        expected_required = set(expected)
    if set(required) != expected_required:
        errors.append(
            f"{name} required fields differ from the native callback contract"
        )
    for field, expected_schema in expected.items():
        if _schema_contract(properties.get(field)) != expected_schema:
            errors.append(
                f"{name} field {field} differs from the native input contract"
            )


@dataclass(frozen=True)
class ContractReport:
    server_name: str
    server_version: str
    protocol_version: str
    tool_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _json_result(payload: dict[str, Any], method: str) -> dict[str, Any]:
    if "error" in payload:
        raise ValueError(f"{method} returned JSON-RPC error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"{method} did not return a result object")
    return result


def _contains_marker(value: Any, marker: str) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_marker(key, marker) or _contains_marker(item, marker)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_marker(item, marker) for item in value)
    return isinstance(value, str) and marker in value


def inspect_contract(
    initialize: dict[str, Any],
    tools_list: dict[str, Any],
    resources_list: dict[str, Any],
) -> ContractReport:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        initialize_result = _json_result(initialize, "initialize")
    except ValueError as exc:
        return ContractReport("unknown", "unknown", "unknown", 0, (str(exc),), ())

    server_info = initialize_result.get("serverInfo")
    capabilities = initialize_result.get("capabilities")
    protocol_version = initialize_result.get("protocolVersion")
    if not isinstance(server_info, dict):
        errors.append("initialize is missing serverInfo")
        server_info = {}
    if server_info.get("name") != SERVER_NAME:
        errors.append(f"initialize server identity must be {SERVER_NAME!r}")
    if (
        not isinstance(server_info.get("version"), str)
        or not server_info["version"].strip()
    ):
        errors.append("initialize is missing a nonempty server version")
    if not isinstance(capabilities, dict):
        errors.append("initialize is missing capabilities")
        capabilities = {}
    if not isinstance(capabilities.get("tools"), dict):
        errors.append("initialize is missing the tools capability")
    if not isinstance(protocol_version, str) or not protocol_version:
        errors.append("initialize is missing protocolVersion")
        protocol_version = "unknown"
    if protocol_version != PROTOCOL_VERSION:
        errors.append(
            f"unsupported protocol version {protocol_version!r}; expected {PROTOCOL_VERSION}"
        )

    tools_result: dict[str, Any]
    try:
        tools_result = _json_result(tools_list, "tools/list")
    except ValueError as exc:
        errors.append(str(exc))
        tools_result = {}
    tools = tools_result.get("tools", [])
    if not isinstance(tools, list):
        errors.append("tools/list did not return a tools array")
        tools = []

    tool_names = {
        tool.get("name")
        for tool in tools
        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
    }
    for required in NATIVE_DIALOG_TOOLS:
        if required not in tool_names:
            errors.append(f"tools/list is missing {required}")
    seen: set[str] = set()
    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            errors.append("tools/list contains a malformed tool definition")
            continue
        if tool["name"] in seen:
            errors.append(f"tools/list contains duplicate tool {tool['name']}")
        seen.add(tool["name"])
        _inspect_input_schema(tool, errors)
    if not tool_names - set(NATIVE_DIALOG_TOOLS):
        errors.append("tools/list contains no protected business tools")
    if tools_result.get("nextCursor"):
        errors.append(
            "tools/list pagination is incomplete; inspect remaining catalog pages"
        )

    for marker in UI_MARKERS:
        if _contains_marker(initialize, marker) or _contains_marker(tools_list, marker):
            errors.append(f"text-only contract exposes UI metadata: {marker}")

    try:
        resources_result = _json_result(resources_list, "resources/list")
    except ValueError as exc:
        errors.append(str(exc))
        resources_result = {}
    if resources_result.get("nextCursor"):
        errors.append(
            "resources/list pagination is incomplete; inspect remaining catalog pages"
        )
    resources = resources_result.get("resources", [])
    if not isinstance(resources, list):
        errors.append("resources/list did not return a resources array")
        resources = []
    for marker in UI_MARKERS[1:]:
        if _contains_marker(resources, marker):
            errors.append(f"text-only contract publishes UI resource: {marker}")

    check_tool = next(
        (
            tool
            for tool in tools
            if isinstance(tool, dict) and tool.get("name") == "erp_dialog_check"
        ),
        None,
    )
    if isinstance(check_tool, dict):
        annotations = check_tool.get("annotations", {})
        expected_annotations = {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
        if not isinstance(annotations, dict):
            errors.append("erp_dialog_check is missing safety annotations")
        else:
            for key, expected in expected_annotations.items():
                if annotations.get(key) is not expected:
                    errors.append(
                        f"erp_dialog_check annotation {key} must be {expected!r}, "
                        f"got {annotations.get(key)!r}"
                    )

    return ContractReport(
        str(server_info.get("name", "unknown")),
        str(server_info.get("version", "unknown")),
        protocol_version,
        len(tools),
        tuple(errors),
        tuple(warnings),
    )


def post_json(
    url: str, payload: dict[str, Any], timeout: float
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            if not body:
                return response.status, {}
            parsed = json.loads(body.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("MCP response is not a JSON object")
            return response.status, parsed
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"network error for {url}: {exc.reason}") from exc


def run_live_check(url: str, timeout: float) -> ContractReport:
    initialize_status, initialize = post_json(
        url,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "gigma-mcp-live-check", "version": "1"},
            },
        },
        timeout,
    )
    if initialize_status != 200:
        raise RuntimeError(f"initialize returned HTTP {initialize_status}")

    notification_status, _ = post_json(
        url,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        timeout,
    )
    if notification_status not in (200, 202):
        raise RuntimeError(
            f"notifications/initialized returned HTTP {notification_status}"
        )

    tools_status, tools_list = post_json(
        url,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        timeout,
    )
    if tools_status != 200:
        raise RuntimeError(f"tools/list returned HTTP {tools_status}")

    resources_status, resources_list = post_json(
        url,
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}},
        timeout,
    )
    if resources_status != 200:
        raise RuntimeError(f"resources/list returned HTTP {resources_status}")

    return inspect_contract(initialize, tools_list, resources_list)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        report = run_live_check(args.url, args.timeout)
    except (RuntimeError, ValueError) as exc:
        print(f"Live contract check failed: {exc}")
        return 1

    status = "OK" if report.ok else "FAILED"
    print(
        f"Live contract {status}: {report.server_name} {report.server_version}; "
        f"protocol {report.protocol_version}; {report.tool_count} tools"
    )
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
