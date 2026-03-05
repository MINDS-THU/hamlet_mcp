#!/usr/bin/env python
# coding=utf-8
import os
from typing import Any

import requests

from gradio_client import Client
from mcp.server.fastmcp import FastMCP


def _get_env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


BASE_URL = _get_env("HAMLET_BASE_URL", "")
API_NAME = _get_env("HAMLET_API_NAME", "/interact_with_agent")
HANDLE_API_NAME = _get_env("HAMLET_HANDLE_API_NAME", "/handle_prompt")

mcp = FastMCP("hamlet-connector")


def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "answer" in result:
        return str(result["answer"])
    return str(result)


def _resolve_base_url(base_url: str | None) -> str:
    value = (base_url or BASE_URL).strip()
    if not value:
        raise ValueError("Missing base_url. Set HAMLET_BASE_URL or pass base_url.")
    return value


def _resolve_api_name(api_name: str | None) -> str:
    return (api_name or API_NAME).strip() or "/interact_with_agent"


def _resolve_handle_api_name(handle_api_name: str | None) -> str:
    return (handle_api_name or HANDLE_API_NAME).strip() or "/handle_prompt"


def _fetch_service_description(base_url: str) -> str:
    try:
        response = requests.get(f"{base_url}/config", timeout=10)
        response.raise_for_status()
        config = response.json()
    except Exception:
        return "HAMLET Gradio agent"
    title = str(config.get("title") or "").strip()
    desc = str(config.get("description") or "").strip()
    parts = [p for p in [title, desc] if p]
    return " - ".join(parts) if parts else "HAMLET Gradio agent"


@mcp.tool()
def hamlet_info(base_url: str | None = None) -> str:
    """Describe the remote HAMLET service configured by base_url."""
    resolved_base_url = _resolve_base_url(base_url)
    description = _fetch_service_description(resolved_base_url)
    return f"{description} (base_url={resolved_base_url})"


def _extract_last_assistant_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return _stringify_result(messages)
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "assistant":
            return _stringify_result(message.get("content", ""))
    return _stringify_result(messages)


@mcp.tool()
def hamlet_query(
    question: str,
    base_url: str | None = None,
    api_name: str | None = None,
    handle_api_name: str | None = None,
) -> str:
    """Query a HAMLET Gradio API configured by base_url."""
    resolved_base_url = _resolve_base_url(base_url)
    resolved_api_name = _resolve_api_name(api_name)
    resolved_handle_api_name = _resolve_handle_api_name(handle_api_name)
    client = Client(resolved_base_url)
    if resolved_api_name.startswith("/interact_with_agent"):
        try:
            client.predict(question, api_name=resolved_handle_api_name)
        except Exception:
            pass
        messages = []
        result = client.predict(messages, api_name=resolved_api_name)
        return _extract_last_assistant_message(result)
    result = client.predict(question, api_name=resolved_api_name)
    return _stringify_result(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
