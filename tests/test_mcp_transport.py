"""Wire-level metadata probe tests. No callback or tools/call is exercised."""

import copy
import json
import socket
import ssl
import threading
import unittest
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from check_live_contract import LiveCheckError, PROTOCOL_VERSION, main, run_live_check


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/owner_mcp_contract.json").read_text(encoding="utf-8")
)


@dataclass
class Reply:
    status: int = 200
    body: bytes = b""
    content_type: str = "application/json"
    headers: dict = field(default_factory=dict)
    chunks: tuple | None = None
    interval: float = 0
    hold_open: bool = False


class MockMCP:
    def __init__(self, responder):
        self.requests = []
        self.errors = []
        self.release = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def do_GET(self):
                self.do_POST()

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                request = {
                    "http_method": self.command,
                    "payload": json.loads(body) if body else {},
                    "headers": {key.lower(): value for key, value in self.headers.items()},
                    "path": self.path,
                }
                owner.requests.append(request)
                try:
                    response = responder(request)
                except Exception as exc:
                    owner.errors.append(exc)
                    response = Reply(status=500)
                self.send_response(response.status)
                self.send_header("Content-Type", response.content_type)
                self.send_header("Connection", "close")
                if response.chunks is None and "Content-Length" not in response.headers:
                    self.send_header("Content-Length", str(len(response.body)))
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                try:
                    for chunk in response.chunks if response.chunks is not None else (response.body,):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        if response.interval:
                            owner.release.wait(response.interval)
                    if response.hold_open:
                        owner.release.wait(2)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=lambda: self.httpd.serve_forever(poll_interval=0.01), daemon=True
        )
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/mcp/owner/"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.release.set()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        if self.errors and args[0] is None:
            raise AssertionError(self.errors)


def wire_payload(request, resources=True):
    payload = request["payload"]
    key = {
        "initialize": "initialize",
        "tools/list": "tools_list",
        "resources/list": "resources_list",
    }[payload["method"]]
    result = copy.deepcopy(FIXTURE[key])
    result.update(jsonrpc="2.0", id=payload["id"])
    if key == "initialize" and not resources:
        result["result"]["capabilities"].pop("resources")
    return result


def metadata_reply(request, resources=True):
    if request["payload"]["method"] == "notifications/initialized":
        return Reply(status=202)
    return Reply(body=json.dumps(wire_payload(request, resources)).encode())


class MCPTransportTests(unittest.TestCase):
    def assert_failure(self, responder, category, contains=None, timeout=1):
        with MockMCP(responder) as server:
            with self.assertRaises(LiveCheckError) as caught:
                run_live_check(server.url, timeout)
            self.assertEqual(caught.exception.category, category, caught.exception)
            if contains:
                self.assertIn(contains, str(caught.exception))
            return server.requests

    def test_json_metadata_discovery_is_anonymous_and_read_only(self):
        with MockMCP(metadata_reply) as server:
            report = run_live_check(server.url, 1)
            self.assertTrue(report.ok, report.errors)
            self.assertEqual(
                [request["payload"]["method"] for request in server.requests],
                ["initialize", "notifications/initialized", "tools/list", "resources/list"],
            )
            for index, request in enumerate(server.requests):
                headers = request["headers"]
                self.assertEqual(request["http_method"], "POST")
                self.assertIn("application/json", headers["accept"])
                self.assertIn("text/event-stream", headers["accept"])
                for absent in ("authorization", "cookie", "mcp-session-id"):
                    self.assertNotIn(absent, headers)
                if index:
                    self.assertEqual(headers["mcp-protocol-version"], PROTOCOL_VERSION)

    def test_sse_multiline_notifications_and_transport_session(self):
        session_id = "session-for-this-probe-only"

        def responder(request):
            method = request["payload"]["method"]
            if method != "initialize":
                self.assertEqual(request["headers"].get("mcp-session-id"), session_id)
            if method == "notifications/initialized":
                return Reply(status=202)
            payload = json.dumps(wire_payload(request), ensure_ascii=False, indent=2)
            message = "\r\n".join("data: " + line for line in payload.splitlines())
            body = (
                '\ufeff: keepalive\r\n\r\n'
                'event: message\r\ndata: {"jsonrpc":"2.0","method":"notifications/progress",'
                '"params":{"progressToken":"probe","progress":1}}\r\n\r\n'
                "id: event-1\r\nevent: message\r\n" + message + "\r\n\r\n"
            ).encode()
            return Reply(
                content_type="text/event-stream; charset=utf-8",
                headers={"Mcp-Session-Id": session_id} if method == "initialize" else {},
                # Split CRLF and UTF-8 across HTTP reads; do not close the stream
                # until the probe has returned and its context is cleaned up.
                chunks=tuple(body[offset : offset + 7] for offset in range(0, len(body), 7)),
                hold_open=True,
            )

        with MockMCP(responder) as server:
            report = run_live_check(server.url, 1)
            self.assertTrue(report.ok, report.errors)
            self.assertNotIn("mcp-session-id", server.requests[0]["headers"])

    def test_optional_resources_are_not_requested(self):
        with MockMCP(lambda request: metadata_reply(request, resources=False)) as server:
            self.assertTrue(run_live_check(server.url, 1).ok)
            self.assertEqual(
                [request["payload"]["method"] for request in server.requests],
                ["initialize", "notifications/initialized", "tools/list"],
            )

    def test_initialized_requires_202_and_an_empty_body(self):
        for status, body in ((200, b""), (202, b"{}"), (202, b" ")):
            with self.subTest(status=status, body=body):
                def responder(request):
                    if request["payload"]["method"] == "notifications/initialized":
                        return Reply(status=status, body=body)
                    return metadata_reply(request)

                requests = self.assert_failure(responder, "protocol", "202")
                self.assertEqual(len(requests), 2)

    def test_invalid_json_and_content_type_stop_before_initialized(self):
        for body, content_type in (
            (b"not json", "application/json"),
            (b"[]", "application/json"),
            (b"\xff", "application/json"),
            (b"<html>Login</html>", "text/html"),
            (b"", "application/json"),
        ):
            with self.subTest(body=body, content_type=content_type):
                requests = self.assert_failure(
                    lambda _: Reply(body=body, content_type=content_type), "protocol"
                )
                self.assertEqual(len(requests), 1)

    def test_wire_jsonrpc_envelope_and_id_are_validated_at_each_request(self):
        mutations = (
            lambda payload: payload.pop("jsonrpc"),
            lambda payload: payload.update(jsonrpc="1.0"),
            lambda payload: payload.update(id=999),
            lambda payload: payload.update(id=str(payload["id"])),
            lambda payload: payload.update(id=True),
            lambda payload: payload.update(error={"code": -32603, "message": "error"}),
            lambda payload: payload.update(result=[]),
        )
        for method, expected_requests in (("initialize", 1), ("tools/list", 3), ("resources/list", 4)):
            for mutate in mutations:
                with self.subTest(method=method, mutate=mutate):
                    def responder(request):
                        if request["payload"]["method"] != method:
                            return metadata_reply(request)
                        payload = wire_payload(request)
                        mutate(payload)
                        return Reply(body=json.dumps(payload).encode())

                    requests = self.assert_failure(responder, "protocol")
                    self.assertEqual(len(requests), expected_requests)

    def test_jsonrpc_error_is_reported_without_error_data(self):
        def responder(request):
            return Reply(body=json.dumps({
                "jsonrpc": "2.0", "id": request["payload"]["id"],
                "error": {"code": -32602, "message": "Invalid parameters", "data": "secret-session"},
            }).encode())

        with MockMCP(responder) as server:
            with self.assertRaises(LiveCheckError) as caught:
                run_live_check(server.url, 1)
            self.assertEqual(caught.exception.category, "rpc")
            self.assertIn("-32602", str(caught.exception))
            self.assertNotIn("secret-session", str(caught.exception))
            self.assertEqual(len(server.requests), 1)

    def test_malformed_jsonrpc_error_is_not_treated_as_a_server_result(self):
        for error in ("failure", {"code": "-32603", "message": "failure"}, {"code": -32603}):
            with self.subTest(error=error):
                self.assert_failure(
                    lambda _: Reply(body=json.dumps({"jsonrpc": "2.0", "id": 1, "error": error}).encode()),
                    "protocol", "malformed JSON-RPC error",
                )

    def test_sse_failure_cannot_be_mistaken_for_a_metadata_response(self):
        for body, category in (
            (b'data: {"jsonrpc":"2.0","id":2,"result":{}}\n\n', "protocol"),
            (b'data: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n', "protocol"),
            (b'data: invalid json\n\n', "protocol"),
            (b'data: {"jsonrpc":"2.0","id":1,"result":{}}\n', "protocol"),
            (b'data: {"jsonrpc":"2.0","id":99,"method":"ping"}\n\n', "probe_limit"),
            (b'data: {"jsonrpc":"2.0","id":1,"error":{"code":-32603,"message":"failure"}}\n\n', "rpc"),
        ):
            with self.subTest(body=body):
                self.assert_failure(lambda _: Reply(body=body, content_type="text/event-stream"), category)

    def test_redirects_never_rewrite_or_forward_requests(self):
        with MockMCP(metadata_reply) as destination:
            for status in (301, 302, 303, 307, 308):
                with self.subTest(status=status):
                    self.assert_failure(
                        lambda _: Reply(status=status, headers={"Location": destination.url}),
                        "redirect",
                    )
                    self.assertEqual(destination.requests, [])

    def test_transport_session_is_not_forwarded_to_a_redirect_destination(self):
        with MockMCP(metadata_reply) as destination:
            def responder(request):
                if request["payload"]["method"] == "tools/list":
                    self.assertEqual(request["headers"]["mcp-session-id"], "private-transport-id")
                    return Reply(status=307, headers={"Location": destination.url})
                reply = metadata_reply(request)
                if request["payload"]["method"] == "initialize":
                    reply.headers["Mcp-Session-Id"] = "private-transport-id"
                return reply

            self.assert_failure(responder, "redirect")
            self.assertEqual(destination.requests, [])

    def test_auth_errors_do_not_start_an_auth_flow(self):
        for status in (401, 403):
            with self.subTest(status=status):
                requests = self.assert_failure(
                    lambda _: Reply(status=status, headers={"WWW-Authenticate": 'Bearer realm="owner"'}),
                    "http_auth",
                )
                self.assertEqual(len(requests), 1)
                self.assertNotIn("authorization", requests[0]["headers"])

    def test_unsupported_protocol_stops_before_initialized(self):
        def responder(request):
            payload = wire_payload(request)
            payload["result"]["protocolVersion"] = "1900-01-01"
            return Reply(body=json.dumps(payload).encode())

        requests = self.assert_failure(responder, "protocol", "negotiate")
        self.assertEqual(len(requests), 1)

    def test_invalid_transport_session_header_is_rejected(self):
        for session_id in ("", "contains space", "\x7f"):
            with self.subTest(session_id=session_id):
                def responder(request):
                    reply = metadata_reply(request)
                    reply.headers["Mcp-Session-Id"] = session_id
                    return reply

                self.assert_failure(responder, "protocol", "Mcp-Session-Id")

    def test_connection_refusal_is_network_failure_not_contract_incompatibility(self):
        with socket.socket() as bound_but_not_listening:
            bound_but_not_listening.bind(("127.0.0.1", 0))
            port = bound_but_not_listening.getsockname()[1]
            with self.assertRaises(LiveCheckError) as caught:
                run_live_check(f"http://127.0.0.1:{port}/mcp", 0.2)
        self.assertEqual(caught.exception.category, "network")

    def test_truncated_http_body_is_network_failure(self):
        self.assert_failure(
            lambda _: Reply(body=b'{"jsonrpc":', headers={"Content-Length": "1000"}),
            "network", "truncated",
        )

    def test_sse_heartbeats_cannot_extend_the_total_deadline(self):
        self.assert_failure(
            lambda _: Reply(
                content_type="text/event-stream", chunks=(b": heartbeat\n\n",) * 40, interval=0.01
            ),
            "timeout", timeout=0.05,
        )

    def test_socket_timeout_dns_and_tls_errors_have_separate_categories(self):
        for failure, category in (
            (TimeoutError("timed out"), "timeout"),
            (URLError(TimeoutError("timed out")), "timeout"),
            (URLError(socket.gaierror("DNS failed")), "dns"),
            (URLError(ssl.SSLCertVerificationError("certificate failed")), "tls"),
        ):
            with self.subTest(category=category, failure=failure):
                with patch("check_live_contract.build_opener") as opener:
                    opener.return_value.open.side_effect = failure
                    with self.assertRaises(LiveCheckError) as caught:
                        run_live_check("https://example.invalid/mcp", 1)
                self.assertEqual(caught.exception.category, category)

    def test_cli_reports_unavailable_for_transport_failure_without_traceback(self):
        with patch("sys.argv", ["check_live_contract.py"]), patch(
            "check_live_contract.run_live_check", side_effect=LiveCheckError("network", "connection failed")
        ), patch("builtins.print") as output:
            self.assertEqual(main(), 1)
        self.assertIn("unavailable [network]", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
