#!/usr/bin/env python
# coding=utf-8
import os
from typing import Any

import requests
from gradio_client import Client
from mcp.server.fastmcp import FastMCP


DEFAULT_DESCRIPTION = "HAMLET Gradio agent"
DEFAULT_API_NAME = "/interact_with_agent"
DEFAULT_HANDLE_API_NAME = "/handle_prompt"
DEFAULT_INFO_PATHS = (
    "/gradio_api/info?serialize=False",
    "/info?serialize=False",
)


def _get_env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def _get_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


BASE_URL = _get_env("HAMLET_BASE_URL", "")
API_NAME = _get_env("HAMLET_API_NAME", DEFAULT_API_NAME)
HANDLE_API_NAME = _get_env("HAMLET_HANDLE_API_NAME", DEFAULT_HANDLE_API_NAME)
HTTP_TIMEOUT = _get_int_env("HAMLET_HTTP_TIMEOUT", 30)

mcp = FastMCP("hamlet-connector")


def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        if "answer" in result:
            return str(result["answer"])
        if "text" in result:
            return str(result["text"])
        if "value" in result and isinstance(result["value"], str):
            return result["value"]
        if "file" in result:
            return f"[file] {result['file']}"
        if "component" in result:
            return f"[{result['component']}]"
    if isinstance(result, list):
        parts = [_stringify_result(item).strip() for item in result]
        parts = [part for part in parts if part]
        return "\n\n".join(parts)
    return str(result)


def _resolve_base_url(base_url: str | None) -> str:
    value = (base_url or BASE_URL).strip().rstrip("/")
    if not value:
        raise ValueError("Missing base_url. Set HAMLET_BASE_URL or pass base_url.")
    return value


def _resolve_api_name(api_name: str | None) -> str:
    return (api_name or API_NAME).strip() or DEFAULT_API_NAME


def _resolve_handle_api_name(handle_api_name: str | None) -> str:
    return (handle_api_name or HANDLE_API_NAME).strip() or DEFAULT_HANDLE_API_NAME


def _http_get_json(base_url: str, paths: tuple[str, ...] | list[str] | str) -> dict[str, Any]:
    path_list = (paths,) if isinstance(paths, str) else tuple(paths)
    last_error: Exception | None = None
    for path in path_list:
        try:
            response = requests.get(f"{base_url}{path}", timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"value": payload}
        except Exception as exc:
            last_error = exc
    joined_paths = ", ".join(path_list)
    raise RuntimeError(f"Failed to fetch JSON from {base_url} using {joined_paths}.") from last_error


def _fetch_service_config(base_url: str) -> dict[str, Any]:
    try:
        return _http_get_json(base_url, "/config")
    except RuntimeError:
        return {}


def _fetch_api_info(base_url: str) -> dict[str, Any]:
    return _http_get_json(base_url, DEFAULT_INFO_PATHS)


def _named_endpoints(api_info: dict[str, Any]) -> dict[str, dict[str, Any]]:
    endpoints = api_info.get("named_endpoints")
    if not isinstance(endpoints, dict):
        return {}
    return {
        name: spec
        for name, spec in endpoints.items()
        if isinstance(name, str) and isinstance(spec, dict)
    }


def _endpoint_parameters(spec: dict[str, Any]) -> list[dict[str, Any]]:
    parameters = spec.get("parameters")
    if not isinstance(parameters, list):
        return []
    return [parameter for parameter in parameters if isinstance(parameter, dict)]


def _first_parameter_name(spec: dict[str, Any]) -> str:
    parameters = _endpoint_parameters(spec)
    if not parameters:
        return ""
    name = parameters[0].get("parameter_name")
    return str(name).strip() if name is not None else ""


def _is_message_history_endpoint(spec: dict[str, Any]) -> bool:
    return _first_parameter_name(spec) == "messages"


def _is_prompt_endpoint(spec: dict[str, Any]) -> bool:
    return _first_parameter_name(spec) in {"prompt", "question", "task", "text", "input"}


def _pick_endpoint(
    preferred: str | None,
    candidates: list[str],
    endpoints: dict[str, dict[str, Any]],
    label: str,
) -> str | None:
    endpoint_names = sorted(endpoints)
    if preferred:
        if preferred in endpoints:
            return preferred
        suffixed = [name for name in endpoint_names if name == preferred or name.startswith(f"{preferred}_")]
        if len(suffixed) == 1:
            return suffixed[0]
        available = ", ".join(endpoint_names) or "none"
        raise ValueError(f"{label} endpoint '{preferred}' not found. Available endpoints: {available}")

    for candidate in candidates:
        if candidate in endpoints:
            return candidate
    for candidate in candidates:
        for name in endpoint_names:
            if name.startswith(f"{candidate}_"):
                return name
    return None


def _discover_query_endpoint(
    preferred: str | None,
    endpoints: dict[str, dict[str, Any]],
) -> str:
    endpoint = _pick_endpoint(preferred, [DEFAULT_API_NAME], endpoints, "Query")
    if endpoint:
        return endpoint

    for name in sorted(endpoints):
        if "interact" in name and _is_message_history_endpoint(endpoints[name]):
            return name
    for name in sorted(endpoints):
        if _is_prompt_endpoint(endpoints[name]):
            return name

    available = ", ".join(sorted(endpoints)) or "none"
    raise ValueError(f"Could not discover a query endpoint. Available endpoints: {available}")


def _discover_handle_endpoint(
    preferred: str | None,
    endpoints: dict[str, dict[str, Any]],
) -> str:
    endpoint = _pick_endpoint(preferred, [DEFAULT_HANDLE_API_NAME], endpoints, "Prompt")
    if endpoint:
        return endpoint

    for name in sorted(endpoints):
        if "handle" in name and "prompt" in name and _is_prompt_endpoint(endpoints[name]):
            return name
    for name in sorted(endpoints):
        if _is_prompt_endpoint(endpoints[name]):
            return name

    available = ", ".join(sorted(endpoints)) or "none"
    raise ValueError(f"Could not discover a prompt endpoint. Available endpoints: {available}")


def _discover_service(
    base_url: str,
    api_name: str | None = None,
    handle_api_name: str | None = None,
) -> dict[str, Any]:
    api_info = _fetch_api_info(base_url)
    endpoints = _named_endpoints(api_info)
    query_api_name = _discover_query_endpoint(api_name, endpoints)
    query_spec = endpoints[query_api_name]
    uses_message_history = _is_message_history_endpoint(query_spec)
    prompt_api_name = None
    if uses_message_history:
        prompt_api_name = _discover_handle_endpoint(handle_api_name, endpoints)

    return {
        "api_info": api_info,
        "endpoints": endpoints,
        "api_name": query_api_name,
        "api_spec": query_spec,
        "handle_api_name": prompt_api_name,
        "init_api_name": _pick_endpoint(None, ["/init_session"], endpoints, "Init"),
    }


def _fetch_service_description(base_url: str, service: dict[str, Any]) -> str:
    config = _fetch_service_config(base_url)
    title = str(config.get("title") or "").strip()
    desc = str(config.get("description") or "").strip()

    parts = [part for part in [title, desc] if part and part.lower() != "gradio"]
    if parts:
        return " - ".join(parts)

    query_api_name = service.get("api_name") or DEFAULT_API_NAME
    return f"{DEFAULT_DESCRIPTION} via {query_api_name}"


def _extract_last_assistant_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return _stringify_result(messages)

    assistant_messages: list[str] = []
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "assistant":
            text = _stringify_result(message.get("content", "")).strip()
            if text:
                assistant_messages.append(text)

    if not assistant_messages:
        return _stringify_result(messages)

    for text in reversed(assistant_messages):
        if "Final answer" in text or "最终答案" in text:
            return text
    return assistant_messages[-1]


def _call_predict(client: Client, api_name: str, *args: Any) -> Any:
    try:
        return client.predict(*args, api_name=api_name)
    except Exception as exc:
        raise RuntimeError(f"Call to {api_name} failed: {exc}") from exc


@mcp.tool()
def hamlet_info(base_url: str | None = None) -> str:
    """Describe the remote HAMLET service configured by base_url and show the resolved endpoints."""
    resolved_base_url = _resolve_base_url(base_url)
    service = _discover_service(resolved_base_url)
    description = _fetch_service_description(resolved_base_url, service)
    endpoint_names = ", ".join(sorted(service["endpoints"])) or "none"
    lines = [
        f"Description: {description}",
        f"Base URL: {resolved_base_url}",
        f"Query endpoint: {service['api_name']}",
        f"Prompt endpoint: {service['handle_api_name'] or 'not required'}",
        f"Init endpoint: {service['init_api_name'] or 'not exposed'}",
        f"Available endpoints: {endpoint_names}",
    ]
    return "\n".join(lines)


@mcp.tool()
def hamlet_query(
    question: str,
    base_url: str | None = None,
    api_name: str | None = None,
    handle_api_name: str | None = None,
) -> str:
    """Query a HAMLET Gradio service. Endpoints are auto-discovered unless overridden."""
    resolved_base_url = _resolve_base_url(base_url)
    preferred_api_name = _resolve_api_name(api_name) if api_name else None
    preferred_handle_api_name = _resolve_handle_api_name(handle_api_name) if handle_api_name else None
    service = _discover_service(
        resolved_base_url,
        api_name=preferred_api_name,
        handle_api_name=preferred_handle_api_name,
    )
    client = Client(resolved_base_url)

    init_api_name = service.get("init_api_name")
    if init_api_name:
        try:
            _call_predict(client, init_api_name)
        except RuntimeError:
            pass

    query_api_name = service["api_name"]
    query_spec = service["api_spec"]

    if _is_message_history_endpoint(query_spec):
        prompt_api_name = service["handle_api_name"]
        if not prompt_api_name:
            raise ValueError(f"Endpoint {query_api_name} requires a prompt endpoint, but none was found.")
        _call_predict(client, prompt_api_name, question)
        result = _call_predict(client, query_api_name, [])
        return _extract_last_assistant_message(result)

    if _is_prompt_endpoint(query_spec):
        result = _call_predict(client, query_api_name, question)
        return _stringify_result(result)

    parameter_names = ", ".join(
        parameter.get("parameter_name", "?") for parameter in _endpoint_parameters(query_spec)
    ) or "none"
    raise ValueError(
        f"Unsupported endpoint signature for {query_api_name}. Parameters: {parameter_names}"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
