# Student AGENTS.md template

Use this file to describe when the HAMLET connector should be called and which base_url to use.

## Tools

- hamlet-connector.hamlet_info: Call once to learn the tool description for the chosen base_url.
- hamlet-connector.hamlet_query: Use for queries at that base_url. Input is a plain English question.

## Example tasks

Step 1: Identify the target service.
Call hamlet-connector.hamlet_info with base_url="<your-private-hamlet-url>".

Step 2: Run a task.
Call hamlet-connector.hamlet_query with question="<your question>" and base_url="<your-private-hamlet-url>".
