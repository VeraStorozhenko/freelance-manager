import json
import unittest

import httpx

from app.mcp import (
    MCPSessionData,
    NotionMCPClient,
    generate_code_challenge,
    generate_code_verifier,
)


class MCPTests(unittest.TestCase):
    def test_pkce_helpers_return_url_safe_values(self):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)

        self.assertTrue(verifier)
        self.assertTrue(challenge)
        self.assertNotIn("=", verifier)
        self.assertNotIn("=", challenge)

    def test_list_tools_and_call_tool_use_mcp_jsonrpc(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content.decode())
            calls.append((request.url.path, request.headers, payload))
            if payload["method"] == "initialize":
                return httpx.Response(
                    200,
                    headers={"mcp-session-id": "remote-session"},
                    json={"jsonrpc": "2.0", "id": "initialize", "result": {"serverInfo": {"name": "notion"}}},
                )
            if payload["method"] == "notifications/initialized":
                return httpx.Response(200, json={})
            if payload["method"] == "tools/list":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": "tools-list",
                        "result": {
                            "tools": [
                                {
                                    "name": "notion-search",
                                    "description": "Search Notion",
                                    "inputSchema": {"type": "object", "properties": {}},
                                }
                            ]
                        },
                    },
                )
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": "call-notion-search",
                    "result": {"content": [{"type": "text", "text": "ok"}]},
                },
            )

        client = NotionMCPClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            server_url="https://mcp.notion.com/mcp",
        )
        session = MCPSessionData(
            session_id="session",
            access_token="token",
        )

        tools = client.list_tools(session)
        result = client.call_tool(session, "notion-search", {"query": "Acme"})

        self.assertEqual(tools[0]["name"], "notion-search")
        self.assertEqual(result["content"][0]["text"], "ok")
        self.assertEqual(session.mcp_session_id, "remote-session")
        self.assertTrue(any("mcp-session-id" in headers for _, headers, _ in calls[2:]))


if __name__ == "__main__":
    unittest.main()
