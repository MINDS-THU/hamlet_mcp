# AGENTS.md template for opencode + HAMLET MCP

Use this file to tell opencode when it should forward a task to a HAMLET Gradio agent through the local MCP server.

## Tools

- hamlet-connector.hamlet_info: Call first to inspect the configured HAMLET service and confirm which endpoints were resolved.
- hamlet-connector.hamlet_query: Use this to send a natural-language question to the HAMLET agent and return the final answer.

## When to use the HAMLET connector

- Use it for operations research, optimization, scheduling, planning, simulation, integer programming, linear programming, and solver-related questions.
- If the user gives a specific HAMLET URL, pass it as `base_url`.
- If the user does not specify a URL, use the default `HAMLET_BASE_URL` configured in the MCP server environment.

## Recommended calling pattern

Step 1: Inspect the service.
Call `hamlet-connector.hamlet_info`.

Step 2: Send the task.
Call `hamlet-connector.hamlet_query` with the user's question.

## Example

User asks: `请帮我把这个生产排程问题建成整数规划模型。`

Suggested tool flow:

1. `hamlet-connector.hamlet_info`
2. `hamlet-connector.hamlet_query(question="请帮我把这个生产排程问题建成整数规划模型。")`
