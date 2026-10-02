"""Exercise the real browser and agent with a local page and mocked API."""
import argparse
import http.server
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid
from unittest.mock import patch

import agent

requests = []
test_handoff = "--test-handoff" in sys.argv
test_start_pause = "--test-start-pause" in sys.argv
# Avoid restoring dead fixture URLs from a previous run's browser journal.
os.environ["BWB_USER_DATA_DIR"] = str(Path(__file__).resolve().parents[2] / ".local-test" / (
    "smoke-profile-" + uuid.uuid4().hex))


class Handler(http.server.BaseHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except ConnectionResetError:
            # Chrome can close speculative/keep-alive sockets during cleanup.
            # This is not a failure of the page or mocked API assertions.
            pass

    def do_GET(self):
        body = b'''<!doctype html><html><head><title>Local browser smoke</title></head>
        <body><h1>Browser fixture</h1><button id="continue"
        onclick="document.querySelector('h1').textContent='Clicked successfully'">
        Continue</button></body></html>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append(payload)
        steps = [("browser_click", {"selector": "#continue"}),
                 ("browser_text", {}), ("browser_status", {})]
        if test_handoff:
            steps[0] = ("agent_manual_captcha", {})
        if test_start_pause:
            steps = steps[1:]
        if len(requests) <= len(steps):
            name, arguments = steps[len(requests) - 1]
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call_{len(requests)}", "type": "function", "function": {
                    "name": name, "arguments": json.dumps(arguments)}}]}
        else:
            message = {"role": "assistant", "content": "Local browser smoke complete"}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"choices": [{"message": message}]}).encode())

    def log_message(self, *_):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
origin = f"http://127.0.0.1:{server.server_port}"
deadline = time.monotonic() + 60
client = None
try:
    client = agent.MCPClient(Path(os.environ["BWB_SERVER_DIR"]), deadline)
    client.initialize()
    tools = client.list_tools()
    # Force a real CDP connection before navigating to the local fixture.
    startup = client.call_tool("browser_text", {})
    assert not startup.get("isError"), agent.observation(startup)
    options = argparse.Namespace(url=origin + "/page", goal="Click Continue and report title/URL",
                                 model="mock/local", max_steps=5, manual_captcha=test_handoff,
                                 pause_before_agent=test_start_pause)

    def simulate_user():
        # This is an ordinary local fixture button, not a real CAPTCHA.
        if test_start_pause:
            assert not requests, "API request occurred before initial handoff"
        result = client.call_tool("browser_click", {"selector": "#continue"})
        assert not result.get("isError"), agent.observation(result)
        return ""

    with patch.object(agent, "API_URL", origin + "/mock-api"), \
            patch("builtins.input", side_effect=simulate_user):
        result = agent.run_agent(client, tools, options,
            lambda payload: agent.openrouter_request(payload, "test-key", deadline), deadline)
    assert result == "Local browser smoke complete", result
    assert len(requests) == (3 if test_start_pause else 4), len(requests)
    assert "Clicked successfully" in requests[-2]["messages"][-1]["content"], json.dumps([
        request["messages"][-1] for request in requests[1:]], indent=2)
    status = requests[-1]["messages"][-1]["content"]
    assert '"connected":true' in status, status
    assert "Local browser smoke" in status, status
    assert origin + "/page" in status, status
    print("PASS: real Chrome navigation, click, page text, title/URL, and mocked HTTP tool loop")
    if test_handoff:
        print("PASS: simulated manual handoff keeps the same real browser session and resumes")
    if test_start_pause:
        assert "Clicked successfully" in requests[0]["messages"][-1]["content"]
        print("PASS: initial handoff occurs before API requests and resumes on the user's page")
finally:
    if client:
        try:
            # Upstream's restart tool stops managed Chrome without immediately relaunching it.
            client.call_tool("browser_restart", {})
        finally:
            client.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
