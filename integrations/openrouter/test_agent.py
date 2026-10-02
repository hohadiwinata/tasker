import argparse
import copy
import http.server
import io
import json
import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

import agent


TOOLS = [
    {"name": "browser_goto", "inputSchema": {"type": "object"}},
    {"name": "browser_status", "inputSchema": {"type": "object"}},
    {"name": "browser_eval", "inputSchema": {"type": "object"}},
    {"name": "browser_download", "inputSchema": {"type": "object"}},
]


def args(max_steps=25, url="https://example.com"):
    return argparse.Namespace(url=url, goal="Report the destination", model="test/model",
                              max_steps=max_steps)


def tool_reply(name="browser_status", arguments="{}"):
    return {"choices": [{"finish_reason": "tool_calls", "message": {
        "role": "assistant", "content": None, "tool_calls": [{
            "id": "call_1", "type": "function", "function": {
                "name": name, "arguments": arguments}}]}}]}


class FakeClient:
    def __init__(self):
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "browser_status":
            return {"content": [{"type": "text", "text": '{"connected":true}'}]}
        return {"content": [{"type": "text", "text": "page fixture"}]}


class AgentTests(unittest.TestCase):
    def test_headless_setting_is_passed_as_explicit_server_argument(self):
        for value in ("false", "true"):
            with self.subTest(value=value), patch.dict(os.environ, {"BWB_HEADLESS": value}), \
                    patch("agent.subprocess.Popen") as popen, patch("agent.threading.Thread"):
                agent.MCPClient(Path("fixture"), time.monotonic() + 10)
                self.assertEqual(popen.call_args.args[0][-2:], ["--headless", value])

    def test_failed_browser_start_does_not_pause_or_call_api(self):
        options = args()
        options.pause_before_agent = True
        with patch.object(FakeClient, "call_tool", return_value={"isError": True,
                "content": [{"type": "text", "text": "Browser exited"}]}), \
                patch("builtins.input", side_effect=AssertionError("Must not pause")), \
                self.assertRaisesRegex(RuntimeError, "Could not open the visible browser"):
            agent.run_agent(FakeClient(), TOOLS, options,
                            lambda _: self.fail("API called before browser started"), time.monotonic() + 10)

    def test_start_pause_happens_before_api_and_preserves_user_page(self):
        client = FakeClient()
        options = args()
        options.pause_before_agent = True
        requests = []

        def user_input():
            self.assertEqual(requests, [])
            return ""

        def request(payload):
            requests.append(copy.deepcopy(payload))
            self.assertEqual([name for name, _ in client.calls],
                             ["browser_text", "browser_status", "browser_goto", "browser_text", "browser_status"])
            self.assertIn("user's current page", payload["messages"][-1]["content"])
            self.assertIn("agent_manual_captcha", [tool["function"]["name"] for tool in payload["tools"]])
            return {"choices": [{"message": {"content": "Resumed from user page"}}]}

        with patch("builtins.input", side_effect=user_input), patch("sys.stderr", io.StringIO()):
            result = agent.run_agent(client, TOOLS, options, request, time.monotonic() + 10)
        self.assertEqual(result, "Resumed from user page")

    def test_start_pause_quit_makes_no_api_request(self):
        options = args()
        options.pause_before_agent = True
        with patch("builtins.input", return_value="q"), patch("sys.stderr", io.StringIO()), \
                self.assertRaises(agent.ManualHandoffStopped):
            agent.run_agent(FakeClient(), TOOLS, options,
                            lambda _: self.fail("API called during initial pause"), time.monotonic() + 10)

    def test_manual_captcha_tool_is_opt_in(self):
        default = {tool["function"]["name"] for tool in agent.select_tools(TOOLS)}
        manual = {tool["function"]["name"] for tool in agent.select_tools(TOOLS, True)}
        self.assertNotIn("agent_manual_captcha", default)
        self.assertIn("agent_manual_captcha", manual)

    def test_manual_pause_extends_deadline_and_reads_same_session(self):
        client = FakeClient()
        with patch("builtins.input", return_value=""), \
                patch("agent.time.monotonic", side_effect=[100, 145]), \
                patch("sys.stderr", io.StringIO()):
            text, deadline = agent.pause_for_captcha(client, 110)
        self.assertEqual(deadline, 155)
        self.assertEqual(client.deadline, deadline)
        self.assertEqual([name for name, _ in client.calls], ["browser_text", "browser_status"])
        self.assertIn("Check whether verification is complete", text)

    def test_manual_pause_quit_and_eof_stop(self):
        for kwargs in ({"return_value": "q"}, {"side_effect": EOFError}):
            client = FakeClient()
            with self.subTest(kwargs=kwargs), patch("builtins.input", **kwargs), \
                    patch("sys.stderr", io.StringIO()), \
                    self.assertRaises(agent.ManualHandoffStopped):
                agent.pause_for_captcha(client, time.monotonic() + 10)
            self.assertEqual(client.calls, [])

    def test_agent_resumes_after_manual_handoff_without_renavigating(self):
        client = FakeClient()
        options = args()
        options.manual_captcha = True
        requests = []

        def request(payload):
            requests.append(copy.deepcopy(payload))
            if len(requests) == 1:
                return tool_reply("agent_manual_captcha")
            return {"choices": [{"message": {"content": "Resumed"}}]}

        with patch("builtins.input", return_value=""), patch("sys.stderr", io.StringIO()):
            result = agent.run_agent(client, TOOLS, options, request, time.monotonic() + 10)
        self.assertEqual(result, "Resumed")
        self.assertEqual([name for name, _ in client.calls],
                         ["browser_goto", "browser_text", "browser_status"])
        self.assertEqual(requests[1]["messages"][-1]["role"], "tool")
        self.assertIn("manual verification", requests[1]["messages"][-1]["content"])

    def test_manual_quit_is_not_sent_back_to_model_as_tool_error(self):
        options = args()
        options.manual_captcha = True
        with patch("builtins.input", return_value="q"), patch("sys.stderr", io.StringIO()), \
                self.assertRaises(agent.ManualHandoffStopped):
            agent.run_agent(FakeClient(), TOOLS, options,
                            lambda _: tool_reply("agent_manual_captcha"), time.monotonic() + 10)

    def test_resume_reads_current_page_without_navigating(self):
        client = FakeClient()
        options = args()
        options.resume = True
        requests = []

        def request(payload):
            requests.append(copy.deepcopy(payload))
            return {"choices": [{"message": {"content": "Current page inspected"}}]}

        result = agent.run_agent(client, TOOLS, options, request, time.monotonic() + 10)
        self.assertEqual(result, "Current page inspected")
        self.assertEqual([name for name, _ in client.calls], ["browser_text", "browser_status"])
        self.assertIn("Do not navigate back", requests[0]["messages"][-1]["content"])

    def test_resume_requires_an_attached_browser(self):
        with patch.dict(os.environ, {"BWB_ATTACH_PORT": "0"}), \
                patch("sys.argv", ["agent.py", "--resume", "--check"]), \
                patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as caught:
            agent.main()
        self.assertEqual(caught.exception.code, 2)

    def test_verbose_logs_only_resource_footer(self):
        client = object.__new__(agent.MCPClient)
        client.verbose = True
        footer = "[bwb resources] mcp:70MB browser:410MB tabs:1 state:critical]"
        result = {"content": [{"type": "text", "text": "Private page text"},
                              {"type": "text", "text": footer}]}
        output = io.StringIO()
        with patch.object(client, "request", return_value=result), patch("sys.stderr", output):
            self.assertEqual(client.call_tool("browser_text", {}), result)
        self.assertEqual(output.getvalue().strip(), footer)

    def test_key_not_in_child_environment(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-secret",
                                     "OPENROUTER_MODEL": "test/model",
                                     "BWB_HEADLESS": "true"}):
            env = agent.mcp_environment()
        self.assertNotIn("OPENROUTER_API_KEY", env)
        self.assertNotIn("OPENROUTER_MODEL", env)
        self.assertEqual(env["BWB_HEADLESS"], "true")

    def test_unsafe_tools_not_offered_or_executed(self):
        offered = {tool["function"]["name"] for tool in agent.select_tools(TOOLS)}
        self.assertNotIn("browser_eval", offered)
        self.assertNotIn("browser_download", offered)
        client = FakeClient()
        with self.assertRaises(ValueError):
            agent.execute_tool(client, "browser_eval", {}, offered, time.monotonic() + 10)
        self.assertEqual(client.calls, [])

    def test_observations_are_bounded(self):
        result = {"content": [{"type": "text", "text": "a" * 50000}]}
        text = agent.observation(result)
        self.assertLess(len(text), agent.MAX_OBSERVATION + 100)
        self.assertIn("truncated", text)

    def test_navigation_rejects_javascript_and_file_urls(self):
        client = FakeClient()
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                agent.execute_tool(client, "browser_goto", {"url": url},
                                   {"browser_goto"}, time.monotonic() + 10)
        self.assertEqual(client.calls, [])

    def test_tool_response_preserves_model_reasoning_details(self):
        requests = []
        details = [{"type": "reasoning.encrypted", "data": "test-signature"}]

        def request(payload):
            requests.append(copy.deepcopy(payload))
            if len(requests) == 1:
                response = tool_reply()
                response["choices"][0]["message"]["reasoning_details"] = details
                return response
            return {"choices": [{"message": {"content": "Done"}}]}

        agent.run_agent(FakeClient(), TOOLS, args(), request, time.monotonic() + 10)
        self.assertEqual(requests[1]["messages"][-2]["reasoning_details"], details)

    def test_wait_is_bounded_by_deadline(self):
        with self.assertRaises(TimeoutError):
            agent.execute_tool(FakeClient(), "agent_wait", {"seconds": 30},
                               {"agent_wait"}, time.monotonic() + 1)
        with self.assertRaises(ValueError):
            agent.execute_tool(FakeClient(), "agent_wait", {"seconds": True},
                               {"agent_wait"}, time.monotonic() + 60)

    def test_tool_budget_excludes_initial_navigation(self):
        client = FakeClient()
        requests = []

        def request(payload):
            requests.append(copy.deepcopy(payload))
            return tool_reply()

        result = agent.run_agent(client, TOOLS, args(max_steps=1), request,
                                 time.monotonic() + 10)
        self.assertIn("budget exhausted", result)
        self.assertEqual([name for name, _ in client.calls], ["browser_goto", "browser_status"])
        self.assertEqual(len(requests), 2)

    def test_unknown_tool_returns_error_to_model(self):
        client = FakeClient()
        captured = []

        def request(payload):
            captured.append(copy.deepcopy(payload))
            if len(captured) == 1:
                return tool_reply("browser_download")
            return {"choices": [{"message": {"content": "Blocked"}}]}

        result = agent.run_agent(client, TOOLS, args(), request, time.monotonic() + 10)
        self.assertEqual(result, "Blocked")
        self.assertEqual(len(client.calls), 1)
        self.assertIn("not enabled", captured[1]["messages"][-1]["content"])

    def test_malformed_arguments_are_reported(self):
        client = FakeClient()
        requests = []

        def request(payload):
            requests.append(copy.deepcopy(payload))
            if len(requests) == 1:
                return tool_reply(arguments="not-json")
            return {"choices": [{"message": {"content": "Stopped"}}]}

        agent.run_agent(client, TOOLS, args(), request, time.monotonic() + 10)
        self.assertEqual(len(client.calls), 1)
        self.assertIn("Tool error", requests[1]["messages"][-1]["content"])

    def test_truncated_model_response_not_claimed_as_success(self):
        with self.assertRaises(RuntimeError):
            agent.run_agent(FakeClient(), TOOLS, args(), lambda _: {
                "choices": [{"finish_reason": "length", "message": {"content": "Done"}}]},
                time.monotonic() + 10)


@unittest.skipUnless(os.environ.get("BWB_TEST_SERVER_DIR"),
                     "Set BWB_TEST_SERVER_DIR to an installed bwb checkout")
class MCPIntegrationTests(unittest.TestCase):
    def test_real_mcp_and_mock_http_tool_roundtrip(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = ("<!doctype html><html><head><title>Fixture</title></head>"
                        "<body><article><h1>Local fixture</h1><p>" +
                        "This is a long static page used to test the browser client. " * 30 +
                        "</p></article></body></html>").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(payload)
                response = tool_reply() if len(requests) == 1 else {
                    "choices": [{"message": {"content": "Fixture complete"}}]}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            def log_message(self, *_):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        deadline = time.monotonic() + 30
        client = agent.MCPClient(Path(os.environ["BWB_TEST_SERVER_DIR"]), deadline)
        try:
            client.initialize()
            tools = client.list_tools()
            self.assertEqual(len(tools), 26)
            with patch.object(agent, "API_URL", origin + "/mock-api"):
                result = agent.run_agent(client, tools, args(url=origin + "/page"),
                    lambda payload: agent.openrouter_request(payload, "test-key", deadline), deadline)
            self.assertEqual(result, "Fixture complete")
            self.assertEqual(len(requests), 2)
            self.assertEqual(requests[0]["max_tokens"], 1500)
            self.assertIn("Local fixture", requests[0]["messages"][-1]["content"])
            self.assertEqual(requests[1]["messages"][-1]["role"], "tool")
            self.assertIn('"connected":false', requests[1]["messages"][-1]["content"])
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
