# HAMLET MCP connector

This repository turns a HAMLET Gradio web app into a local MCP server, so tools such as opencode can send questions to a private HAMLET URL.

It is designed for the Gradio UI exposed by HAMLET, including deployments based on:

- `/handle_prompt`
- `/interact_with_agent`
- suffixed variants such as `/handle_prompt_1` and `/interact_with_agent_1`

Version `0.2.0` adds endpoint auto-discovery, clearer error messages, and a more reliable opencode configuration workflow.

## What this MCP server exposes

After opencode starts this local MCP server, two tools are available:

- `hamlet-connector.hamlet_info`: inspect the target HAMLET URL and show the resolved Gradio endpoints.
- `hamlet-connector.hamlet_query`: send one question to the target HAMLET service and return the final assistant answer.

## Prerequisites

- Python `3.10+`
- A reachable HAMLET Gradio URL, for example `http://166.111.59.11:58581`
- `opencode` installed locally if you want to use it from opencode

## Installation

### Option A: using `uv` (recommended)

```bash
cd /path/to/hamlet_mcp
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e .
```

### Option B: using `venv` and `pip`

```bash
cd /path/to/hamlet_mcp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick local verification

Before wiring it into opencode, verify the connector can talk to your HAMLET page.

### 1. Inspect the remote service

```bash
cd /path/to/hamlet_mcp
HAMLET_BASE_URL="http://166.111.59.11:58581" .venv/bin/python - <<'PY'
from hamlet_mcp import hamlet_info
print(hamlet_info())
PY
```

Expected output is a short description plus resolved endpoints such as:

```text
Description: HAMLET Gradio agent via /interact_with_agent
Base URL: http://166.111.59.11:58581
Query endpoint: /interact_with_agent
Prompt endpoint: /handle_prompt
```

### 2. Send a test question

```bash
cd /path/to/hamlet_mcp
HAMLET_BASE_URL="http://166.111.59.11:58581" .venv/bin/python - <<'PY'
from hamlet_mcp import hamlet_query
print(hamlet_query("请用一句话说明你能做什么。"))
PY
```

If this succeeds, the MCP server is ready for opencode.

## Run the MCP server manually

This is useful for debugging.

```bash
cd /path/to/hamlet_mcp
HAMLET_BASE_URL="http://166.111.59.11:58581" \
HAMLET_HTTP_TIMEOUT="30" \
.venv/bin/hamlet-mcp
```

Supported environment variables:

- `HAMLET_BASE_URL`: required unless you always pass `base_url` explicitly
- `HAMLET_API_NAME`: optional override for the query endpoint
- `HAMLET_HANDLE_API_NAME`: optional override for the prompt endpoint
- `HAMLET_HTTP_TIMEOUT`: HTTP metadata timeout in seconds, default `30`

In most cases you do not need to set `HAMLET_API_NAME` or `HAMLET_HANDLE_API_NAME`, because the connector now auto-discovers the right Gradio endpoints.

## Detailed opencode setup

`opencode` starts local MCP servers by reading its config and launching a command array. Because the config schema does not provide a `cwd` field for local MCP servers, use absolute paths in the command.

You can place this config in either of these locations:

- global config: `~/.config/opencode/opencode.json`
- project config: `opencode.json` in your project root

For most HAMLET use cases, project config is the better default because it keeps the MCP server scoped to one repository and makes the setup easier for collaborators to reproduce.

There are two practical ways to configure it.

### Method 1: configure opencode by editing `opencode.json`

If you want this MCP server to be available only inside one project, create:

- `opencode.json` in your project root

If you want it available in every project, edit your user config at:

- macOS: `~/.config/opencode/opencode.json`

Add a local MCP entry like this:

```json
{
	"$schema": "https://opencode.ai/config.json",
	"mcp": {
		"hamlet-or-agent": {
			"type": "local",
			"command": [
				"/absolute/path/to/hamlet_mcp/.venv/bin/python",
				"/absolute/path/to/hamlet_mcp/hamlet_mcp.py"
			],
			"environment": {
				"HAMLET_BASE_URL": "http://166.111.59.11:58581",
				"HAMLET_HTTP_TIMEOUT": "120"
			},
			"timeout": 600000
		}
	}
}
```

Notes:

- `command` must be an array, not a shell string.
- Use absolute paths for both the Python interpreter and `hamlet_mcp.py`.
- `timeout` is in milliseconds on the opencode side. For long optimization tasks, `600000` is a reasonable starting point.
- You can register multiple HAMLET URLs by creating multiple MCP entries with different names and different `HAMLET_BASE_URL` values.
- If you use project config, launch `opencode` from that project directory so it picks up the nearest `opencode.json`.

Example with two different HAMLET services:

```json
{
	"$schema": "https://opencode.ai/config.json",
	"mcp": {
		"hamlet-or-agent": {
			"type": "local",
			"command": [
				"/absolute/path/to/hamlet_mcp/.venv/bin/python",
				"/absolute/path/to/hamlet_mcp/hamlet_mcp.py"
			],
			"environment": {
				"HAMLET_BASE_URL": "http://166.111.59.11:58581"
			},
			"timeout": 600000
		},
		"hamlet-scheduling-agent": {
			"type": "local",
			"command": [
				"/absolute/path/to/hamlet_mcp/.venv/bin/python",
				"/absolute/path/to/hamlet_mcp/hamlet_mcp.py"
			],
			"environment": {
				"HAMLET_BASE_URL": "http://your-other-host:port"
			},
			"timeout": 600000
		}
	}
}
```

### Method 2: add it interactively with `opencode mcp add`

Run:

```bash
opencode mcp add
```

Then choose:

- server type: `local`
- command: the same absolute command array as above, represented in the UI as the local launch command
- environment:
	- `HAMLET_BASE_URL=http://166.111.59.11:58581`
	- optionally `HAMLET_HTTP_TIMEOUT=120`

If the interactive prompt only accepts a single command string in your opencode version, prefer Method 1 and edit `opencode.json` directly, because the JSON format is explicit and less error-prone.

## How to use it inside opencode

### 0. Decide whether to use global config or project config

Recommended:

- use project config if this HAMLET connector is only for one repository
- use global config if you want the same HAMLET connector available everywhere

Project config example layout:

```text
your-project/
├── opencode.json
└── ...
```

### 1. Confirm the MCP server is registered

```bash
opencode mcp list
```

You should see your local `hamlet-*` server in the list.

### 2. Start opencode

```bash
opencode
```

### 3. Ask opencode to use the HAMLET connector

Good examples:

- `Use hamlet-connector.hamlet_info first, then solve this operations research problem with the configured HAMLET service: ...`
- `Use hamlet-connector.hamlet_query to ask the OR HAMLET agent: 请帮我建立一个整数规划模型来描述这个排产问题。`

### 4. Recommended agent instructions

If your project uses an `AGENTS.md`, add guidance so opencode knows when to call the MCP tool. A minimal example is:

```markdown
## Tools

- hamlet-connector.hamlet_info: Call once at the beginning to inspect the configured HAMLET service.
- hamlet-connector.hamlet_query: Use this tool when the user asks an operations research or optimization question that should be forwarded to the HAMLET agent.

## Tool policy

- Prefer hamlet-connector.hamlet_query for optimization modeling, scheduling, planning, simulation, and solver-related questions.
- If the user mentions a specific HAMLET URL, pass it via the tool's `base_url` argument.
- If no URL is specified, use the default URL from the MCP server environment.
```

## Troubleshooting

### `Missing base_url`

You did not provide `HAMLET_BASE_URL` in the MCP server environment, and you did not pass `base_url` in the tool call.

### `Query endpoint ... not found`

Run `hamlet_info` first. It prints the discovered endpoints. If your deployment uses custom names, set:

- `HAMLET_API_NAME`
- `HAMLET_HANDLE_API_NAME`

or pass `api_name` and `handle_api_name` directly in the tool call.

### `Call to /handle_prompt failed` or `Call to /interact_with_agent failed`

Usually one of these is true:

- the HAMLET page is unreachable from your machine
- the Gradio deployment changed its named endpoint layout
- the task takes longer than your opencode MCP timeout

Start by checking:

```bash
cd /path/to/hamlet_mcp
HAMLET_BASE_URL="http://your-host:port" .venv/bin/python - <<'PY'
from hamlet_mcp import hamlet_info
print(hamlet_info())
PY
```

### The task is long and opencode times out

Increase the MCP timeout in `opencode.json`, for example:

```json
{
	"mcp": {
		"hamlet-or-agent": {
			"timeout": 900000
		}
	}
}
```

## Inspect a remote Gradio schema directly

If you want to inspect the remote API yourself:

```bash
cd /path/to/hamlet_mcp
.venv/bin/python - <<'PY'
from gradio_client import Client
print(Client("http://166.111.59.11:58581").view_api())
PY
```
