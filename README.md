# HAMLET MCP connector

This package provides a generic MCP connector for HAMLET Gradio agents, so users can use Claude Code or opencode with their own private service URLs.

## Prerequisites

- Python 3.10+
- The HAMLET Gradio server running (your private URL)

## Install

Using uv:

```bash
uv venv
uv pip install -e .
```

Or pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Use with opencode (recommended)

Users do not need to run the MCP server manually if opencode launches it.

1) Add the MCP server locally from the project folder:

```bash
opencode mcp add
```

Choose:
- Location: Current project
- Server type: Local
- Command: `uv run python hamlet_mcp.py`

2) Set the private base URL in the shell before starting opencode:

```bash
export HAMLET_BASE_URL="http://your-private-host:port"
```

3) Start opencode and use the tools listed in `AGENTS.md`.

## Run MCP server manually

```bash
HAMLET_BASE_URL="http://your-private-host:port" \
HAMLET_API_NAME="/interact_with_agent" \
HAMLET_HANDLE_API_NAME="/handle_prompt" \
hamlet-mcp
```

Defaults:
- HAMLET_BASE_URL: (empty, must be provided)
- HAMLET_API_NAME: /interact_with_agent
- HAMLET_HANDLE_API_NAME: /handle_prompt

If your Gradio endpoints are different, run this once to confirm:

```bash
uv run python -c "from gradio_client import Client; print(Client('http://your-private-host:port').view_api())"
```

## Test locally

```bash
uv run python -c "from hamlet_mcp import hamlet_query; print(hamlet_query('hello', base_url='http://your-private-host:port'))"
```

Then in `AGENTS.md`, describe the tool and when to call it, for example:

```markdown
## Tools

- hamlet-connector.hamlet_info: Call once to learn the tool description for the chosen base_url.
- hamlet-connector.hamlet_query: Use for queries at that base_url. Input is a plain English/Chinese question.
```
