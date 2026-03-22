import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urljoin
from uuid import uuid4

import httpx


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_code_verifier() -> str:
    return _b64url(secrets.token_bytes(32))


def generate_code_challenge(code_verifier: str) -> str:
    return _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())


@dataclass
class MCPSessionData:
    session_id: str
    code_verifier: Optional[str] = None
    oauth_state: Optional[str] = None
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    mcp_session_id: Optional[str] = None
    initialized: bool = False
    last_tools: list[dict] = field(default_factory=list)

    @property
    def connected(self) -> bool:
        return bool(self.access_token)


class MCPSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, MCPSessionData] = {}

    def get(self, session_id: Optional[str]) -> Optional[MCPSessionData]:
        if not session_id:
            return None
        return self._sessions.get(session_id)

    def create(self) -> MCPSessionData:
        session = MCPSessionData(session_id=uuid4().hex)
        self._sessions[session.session_id] = session
        return session

    def get_or_create(self, session_id: Optional[str]) -> MCPSessionData:
        existing = self.get(session_id)
        return existing or self.create()

    def find_by_state(self, state: str) -> Optional[MCPSessionData]:
        return next(
            (session for session in self._sessions.values() if session.oauth_state == state),
            None,
        )

    def reset_connection(self, session: MCPSessionData) -> None:
        session.code_verifier = None
        session.oauth_state = None
        session.client_id = None
        session.access_token = None
        session.refresh_token = None
        session.expires_at = None
        session.mcp_session_id = None
        session.initialized = False
        session.last_tools = []


class NotionMCPClient:
    def __init__(
        self,
        http_client: Optional[httpx.Client] = None,
        server_url: Optional[str] = None,
    ) -> None:
        self._http = http_client or httpx.Client(timeout=30.0, follow_redirects=True)
        self._server_url = server_url or os.getenv("NOTION_MCP_URL", "https://mcp.notion.com/mcp")

    @property
    def server_url(self) -> str:
        return self._server_url

    def discover_auth_metadata(self) -> dict[str, Any]:
        protected_resource_url = self._discover_protected_resource_url()
        resource_metadata = self._http.get(protected_resource_url).json()
        auth_servers = resource_metadata.get("authorization_servers") or []
        if not auth_servers and resource_metadata.get("authorization_server"):
            auth_servers = [resource_metadata["authorization_server"]]
        if not auth_servers and resource_metadata.get("issuer"):
            auth_servers = [resource_metadata["issuer"]]
        if not auth_servers:
            raise RuntimeError(
                f"No authorization server advertised by Notion MCP. Metadata received from "
                f"{protected_resource_url}: {json.dumps(resource_metadata)[:400]}"
            )

        auth_server = auth_servers[0].rstrip("/")
        auth_metadata = self._http.get(
            f"{auth_server}/.well-known/oauth-authorization-server"
        ).json()
        return {
            "authorization_server": auth_server,
            "protected_resource_url": protected_resource_url,
            "resource_metadata": resource_metadata,
            "authorization_metadata": auth_metadata,
        }

    def _discover_protected_resource_url(self) -> str:
        candidates = [
            f"{self._server_url.rstrip('/')}/.well-known/oauth-protected-resource",
            urljoin(self._server_url, "/.well-known/oauth-protected-resource"),
        ]
        seen = set()
        last_error = None

        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                response = self._http.get(candidate)
                response.raise_for_status()
                metadata = response.json()
                if isinstance(metadata, dict) and (
                    metadata.get("authorization_servers")
                    or metadata.get("authorization_server")
                    or metadata.get("issuer")
                ):
                    return candidate
                last_error = RuntimeError(
                    f"Metadata at {candidate} did not include auth server fields: "
                    f"{json.dumps(metadata)[:300]}"
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        raise RuntimeError(
            f"Unable to discover OAuth protected resource metadata for Notion MCP. "
            f"Tried: {', '.join(candidates)}. Last error: {last_error}"
        )

    def register_client(self, redirect_uri: str) -> str:
        metadata = self.discover_auth_metadata()["authorization_metadata"]
        registration_endpoint = metadata.get("registration_endpoint")
        if not registration_endpoint:
            raise RuntimeError("Authorization server did not provide a registration endpoint")

        response = self._http.post(
            registration_endpoint,
            json={
                "client_name": "Freelance OS Copilot",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        response.raise_for_status()
        return response.json()["client_id"]

    def build_authorization_url(
        self,
        session: MCPSessionData,
        redirect_uri: str,
    ) -> str:
        discovery = self.discover_auth_metadata()
        auth_endpoint = discovery["authorization_metadata"]["authorization_endpoint"]
        session.code_verifier = generate_code_verifier()
        session.oauth_state = uuid4().hex
        session.client_id = self.register_client(redirect_uri)

        params = {
            "response_type": "code",
            "client_id": session.client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": generate_code_challenge(session.code_verifier),
            "code_challenge_method": "S256",
            "state": session.oauth_state,
            "resource": self._server_url,
        }
        return f"{auth_endpoint}?{urlencode(params)}"

    def exchange_code(
        self,
        session: MCPSessionData,
        code: str,
        redirect_uri: str,
    ) -> None:
        discovery = self.discover_auth_metadata()
        token_endpoint = discovery["authorization_metadata"]["token_endpoint"]
        response = self._http.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": session.client_id,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": session.code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        self._store_tokens(session, response.json())

    def refresh_access_token(self, session: MCPSessionData) -> None:
        if not session.refresh_token or not session.client_id:
            raise RuntimeError("Missing refresh token for Notion MCP session")

        discovery = self.discover_auth_metadata()
        token_endpoint = discovery["authorization_metadata"]["token_endpoint"]
        response = self._http.post(
            token_endpoint,
            data={
                "grant_type": "refresh_token",
                "client_id": session.client_id,
                "refresh_token": session.refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        self._store_tokens(session, response.json())

    def ensure_valid_token(self, session: MCPSessionData) -> None:
        if not session.access_token:
            raise RuntimeError("Notion MCP is not connected")
        if session.expires_at and session.expires_at <= time.time() + 30:
            self.refresh_access_token(session)

    def list_tools(self, session: MCPSessionData) -> list[dict]:
        self._ensure_initialized(session)
        response = self._rpc(
            session,
            method="tools/list",
            params={},
            request_id="tools-list",
        )
        tools = response.get("result", {}).get("tools", [])
        session.last_tools = tools
        return tools

    def call_tool(self, session: MCPSessionData, name: str, arguments: dict) -> dict:
        self._ensure_initialized(session)
        return self._rpc(
            session,
            method="tools/call",
            params={"name": name, "arguments": arguments},
            request_id=f"call-{name}",
        ).get("result", {})

    def _ensure_initialized(self, session: MCPSessionData) -> None:
        self.ensure_valid_token(session)
        if session.initialized and session.mcp_session_id:
            return

        response = self._rpc(
            session,
            method="initialize",
            params={
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "Freelance OS Copilot",
                    "version": "0.1.0",
                },
            },
            request_id="initialize",
        )
        session.mcp_session_id = response.get("_mcp_session_id", session.mcp_session_id)
        self._rpc(
            session,
            method="notifications/initialized",
            params={},
            request_id=None,
        )
        session.initialized = True

    def _rpc(
        self,
        session: MCPSessionData,
        method: str,
        params: dict,
        request_id: Optional[str],
    ) -> dict:
        self.ensure_valid_token(session)
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        if request_id is not None:
            payload["id"] = request_id

        headers = {
            "Authorization": f"Bearer {session.access_token}",
            "Content-Type": "application/json",
        }
        if session.mcp_session_id:
            headers["mcp-session-id"] = session.mcp_session_id

        response = self._http.post(self._server_url, json=payload, headers=headers)
        response.raise_for_status()

        mcp_session_id = response.headers.get("mcp-session-id")
        data = response.json() if response.content else {"result": {}}
        if mcp_session_id:
            data["_mcp_session_id"] = mcp_session_id
        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Unknown MCP error"))
        return data

    @staticmethod
    def _store_tokens(session: MCPSessionData, payload: dict[str, Any]) -> None:
        session.access_token = payload.get("access_token")
        session.refresh_token = payload.get("refresh_token", session.refresh_token)
        expires_in = payload.get("expires_in")
        session.expires_at = time.time() + expires_in if expires_in else None
        session.mcp_session_id = None
        session.initialized = False
        session.last_tools = []


_session_store = MCPSessionStore()
_mcp_client = NotionMCPClient()


def get_mcp_session_store() -> MCPSessionStore:
    return _session_store


def get_notion_mcp_client() -> NotionMCPClient:
    return _mcp_client
