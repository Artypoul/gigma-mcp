#!/usr/bin/env python3
"""Read-only check for the deployed text-only Gigma owner MCP contract."""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import time
from dataclasses import dataclass, field
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_URL = "https://api.auth.gigma.ru/mcp/owner/"
SERVER_NAME = "Gigma Auth: MCP Owner"
PROTOCOL_VERSION = "2025-06-18"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
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
    if not isinstance(payload, dict):
        raise ValueError(f"{method} response is not a JSON object")
    if "error" in payload:
        error = payload["error"]
        if not isinstance(error, dict):
            raise ValueError(f"{method} returned a malformed JSON-RPC error")
        # Do not echo error.data: it may contain credentials or session details.
        raise ValueError(
            f"{method} returned JSON-RPC error {error.get('code')}: "
            f"{str(error.get('message', 'unknown error'))[:240]}"
        )
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
    resources_list: dict[str, Any] | None = None,
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
    if "resources" in capabilities and not isinstance(capabilities["resources"], dict):
        errors.append("initialize has a malformed resources capability")
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
    tools = tools_result.get("tools")
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

    resources_result: dict[str, Any] = {"resources": []}
    if resources_list is None:
        if isinstance(capabilities.get("resources"), dict):
            errors.append("resources capability advertised but resources/list was not inspected")
    else:
        try:
            resources_result = _json_result(resources_list, "resources/list")
        except ValueError as exc:
            errors.append(str(exc))
            resources_result = {}
    if resources_result.get("nextCursor"):
        errors.append(
            "resources/list pagination is incomplete; inspect remaining catalog pages"
        )
    resources = resources_result.get("resources")
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


class LiveCheckError(RuntimeError):
    """A classified probe failure; network/access failures are not contract verdicts."""

    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


@dataclass
class _TransportSession:
    session_id: str | None = field(default=None, repr=False)


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never rewrite a POST as GET or forward a transport session to a login
        # page/another origin. The caller must supply the canonical MCP URL.
        return None


def _rpc_result(payload: Any, method: str, request_id: int) -> dict[str, Any]:
    """Validate wire envelopes separately from result-only contract fixtures."""
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        raise LiveCheckError("protocol", f"{method} returned an invalid JSON-RPC 2.0 envelope")
    if type(payload.get("id")) is not type(request_id) or payload["id"] != request_id:
        raise LiveCheckError("protocol", f"{method} response id does not match its request")
    if "method" in payload or (("result" in payload) == ("error" in payload)):
        raise LiveCheckError("protocol", f"{method} response must contain exactly one of result/error")
    if "error" in payload:
        error = payload["error"]
        if (
            not isinstance(error, dict)
            or type(error.get("code")) is not int
            or not isinstance(error.get("message"), str)
        ):
            raise LiveCheckError("protocol", f"{method} returned a malformed JSON-RPC error")
    try:
        return _json_result(payload, method)
    except ValueError as exc:
        raise LiveCheckError("rpc" if "error" in payload else "protocol", str(exc)) from exc


def _decode_json(body: bytes | str, method: str) -> Any:
    try:
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return json.loads(body)
    except (UnicodeError, ValueError) as exc:
        raise LiveCheckError("protocol", f"{method} returned invalid UTF-8 JSON") from exc


def _response_chunks(response, deadline: float, method: str):
    size = 0
    while True:
        if time.monotonic() >= deadline:
            raise LiveCheckError("timeout", f"{method} exceeded the response deadline")
        # read1 returns available data, so SSE does not wait for connection close
        # and a stream of heartbeats cannot indefinitely extend the deadline.
        chunk = response.read1(65536)
        if time.monotonic() >= deadline:
            raise LiveCheckError("timeout", f"{method} exceeded the response deadline")
        if not chunk:
            if response.length not in (None, 0):
                raise LiveCheckError("network", f"{method} HTTP response body was truncated")
            return
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise LiveCheckError("probe_limit", f"{method} exceeded the response size limit")
        yield chunk


def _sse_lines(response, deadline: float, method: str):
    pending = b""
    skip_lf = False
    first_line = True
    for chunk in _response_chunks(response, deadline, method):
        if skip_lf and chunk.startswith(b"\n"):
            chunk = chunk[1:]
        skip_lf = False
        pending += chunk
        while match := re.search(br"[\r\n]", pending):
            line, ending = pending[: match.start()], pending[match.start()]
            pending = pending[match.end() :]
            if ending == 13:
                if pending.startswith(b"\n"):
                    pending = pending[1:]
                elif not pending:
                    skip_lf = True
            try:
                decoded = line.decode("utf-8")
            except UnicodeError as exc:
                raise LiveCheckError("protocol", f"{method} returned invalid UTF-8 SSE") from exc
            if first_line:
                decoded = decoded.removeprefix("\ufeff")
                first_line = False
            yield decoded
    # SSE dispatches an event only at a blank line, never an unfinished EOF frame.


def _read_sse(response, deadline: float, method: str, request_id: int) -> dict[str, Any]:
    data: list[str] = []
    event = "message"
    for line in _sse_lines(response, deadline, method):
        if line:
            key, separator, value = line.partition(":")
            if separator and value.startswith(" "):
                value = value[1:]
            if key == "data":
                data.append(value)
            elif key == "event":
                event = value or "message"
            continue
        if data and event == "message":
            message = _decode_json("\n".join(data), method)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise LiveCheckError("protocol", f"{method} returned an invalid SSE JSON-RPC envelope")
            if "method" in message:
                if (
                    not isinstance(message["method"], str)
                    or "result" in message
                    or "error" in message
                    or ("params" in message and not isinstance(message["params"], dict))
                ):
                    raise LiveCheckError("protocol", f"{method} returned a malformed SSE notification/request")
                if "id" in message:
                    raise LiveCheckError(
                        "probe_limit", "server-initiated requests are not executed by this metadata probe"
                    )
                # Notifications can legitimately precede the correlated response.
            else:
                _rpc_result(message, method, request_id)
                return message
        data, event = [], "message"
    raise LiveCheckError("protocol", f"{method} SSE stream ended without a correlated JSON-RPC response")


def _network_failure(exc: BaseException, method: str) -> LiveCheckError:
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, TimeoutError):
        category = "timeout"
    elif isinstance(reason, ssl.SSLError):
        category = "tls"
    elif isinstance(reason, socket.gaierror):
        category = "dns"
    else:
        category = "network"
    return LiveCheckError(category, f"{method} transport failed ({type(reason).__name__})")


def post_json(
    url: str,
    payload: dict[str, Any],
    timeout: float,
    *,
    session: _TransportSession | None = None,
) -> tuple[int, dict[str, Any]]:
    """Post one MCP message, accepting JSON or SSE without auth/redirect fallback."""
    method = payload["method"]
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if method != "initialize":
        headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        if session is not None and session.session_id is not None:
            headers["Mcp-Session-Id"] = session.session_id
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    deadline = time.monotonic() + timeout
    try:
        with build_opener(_NoRedirects()).open(request, timeout=timeout) as response:
            if "id" not in payload:
                if response.status != 202 or response.read(1):
                    raise LiveCheckError(
                        "protocol", f"{method} must return HTTP 202 with no response body"
                    )
                return response.status, {}
            content_type = response.headers.get_content_type()
            if content_type == "text/event-stream":
                parsed = _read_sse(response, deadline, method, payload["id"])
            elif content_type == "application/json":
                parsed = _decode_json(b"".join(_response_chunks(response, deadline, method)), method)
            else:
                raise LiveCheckError("protocol", f"{method} returned unsupported Content-Type {content_type!r}")
            _rpc_result(parsed, method, payload["id"])
            if method == "initialize" and session is not None:
                session_ids = response.headers.get_all("Mcp-Session-Id", [])
                if session_ids:
                    if (
                        len(session_ids) != 1
                        or not session_ids[0]
                        or any(not 0x21 <= ord(char) <= 0x7E for char in session_ids[0])
                    ):
                        raise LiveCheckError("protocol", "initialize returned an invalid Mcp-Session-Id header")
                    session.session_id = session_ids[0]
            return response.status, parsed
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            category, detail = "redirect", "redirect refused; use the canonical MCP URL"
        elif exc.code in (401, 403):
            category, detail = "http_auth", "anonymous metadata discovery denied; no authentication attempted"
        elif exc.code == 404 and session is not None and session.session_id:
            category, detail = "session", "transport session no longer available; rerun discovery"
        else:
            category, detail = "http", "metadata discovery unavailable"
        exc.close()
        raise LiveCheckError(category, f"{method}: HTTP {exc.code}; {detail}") from exc
    except (URLError, OSError, HTTPException) as exc:
        raise _network_failure(exc, method) from exc


def run_live_check(url: str, timeout: float) -> ContractReport:
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    session = _TransportSession()
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
        session=session,
    )
    if not 200 <= initialize_status < 300:
        raise LiveCheckError("http", f"initialize returned HTTP {initialize_status}")
    initialize_result = _rpc_result(initialize, "initialize", 1)
    if initialize_result.get("protocolVersion") != PROTOCOL_VERSION:
        raise LiveCheckError("protocol", f"initialize did not negotiate supported version {PROTOCOL_VERSION}")
    capabilities = initialize_result.get("capabilities")
    if not isinstance(capabilities, dict) or not isinstance(capabilities.get("tools"), dict):
        raise LiveCheckError("protocol", "initialize did not advertise the required tools capability")
    if "resources" in capabilities and not isinstance(capabilities["resources"], dict):
        raise LiveCheckError("protocol", "initialize returned a malformed resources capability")

    notification_status, notification = post_json(
        url,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        timeout,
        session=session,
    )
    if notification_status != 202 or notification:
        raise LiveCheckError(
            "protocol", "notifications/initialized must return HTTP 202 with no response body"
        )

    tools_status, tools_list = post_json(
        url,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        timeout,
        session=session,
    )
    if not 200 <= tools_status < 300:
        raise LiveCheckError("http", f"tools/list returned HTTP {tools_status}")
    _rpc_result(tools_list, "tools/list", 2)

    resources_list = None
    if "resources" in capabilities:
        resources_status, resources_list = post_json(
            url,
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}},
            timeout,
            session=session,
        )
        if not 200 <= resources_status < 300:
            raise LiveCheckError("http", f"resources/list returned HTTP {resources_status}")
        _rpc_result(resources_list, "resources/list", 3)

    return inspect_contract(initialize, tools_list, resources_list)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        report = run_live_check(args.url, args.timeout)
    except LiveCheckError as exc:
        status = "failed" if exc.category in {"protocol", "rpc"} else "unavailable"
        print(f"Live contract check {status} [{exc.category}]: {exc}")
        return 1
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
