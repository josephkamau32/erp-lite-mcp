# ERP-lite MCP Server

An enterprise-ready Model Context Protocol (MCP) server that exposes ERP functionalities to AI agents. Built as a portfolio project to demonstrate AI/ML maturity, this project features a realistic data schema and a critical human-in-the-loop workflow for write actions.

## Overview

As enterprise AI adoption accelerates, providing LLMs with direct read/write access to ERPs is becoming essential. However, autonomous agents should not execute consequential operations (like creating purchase orders or altering system configurations) without human oversight.

This server demonstrates a robust "human-in-the-loop" pattern:
- The AI agent can query **open sales orders**, check **inventory levels**, and identify **low-stock items** using its read-only tools.
- When an agent decides to replenish stock, it can only propose a **purchase requisition** in a `pending_approval` state.
- **The agent cannot approve its own requisition.** A human must intervene to approve it.

## Architecture

```mermaid
graph TD
    Client[Claude Desktop / Custom Client] -->|MCP (stdio or SSE HTTP)| FastMCP[FastMCP Server]
    FastMCP -->|SQLAlchemy| DB[(PostgreSQL Database)]
    DB --> Seed[Seed Data]
```

## Quick Start (Docker)

To get started quickly, run the entire stack with Docker Compose:

```bash
docker compose up
```

This spins up:
- A PostgreSQL database (pre-seeded with realistic enterprise data for sales orders, inventory, and requisitions).
- The MCP server exposing SSE transport at `http://localhost:8000/sse`.

## Tools Exposed

- `get_open_orders(status="open", limit=20)`: Retrieves a list of sales orders by status.
- `check_inventory(material_id)`: Checks the inventory level and computes if it's below the reorder point.
- `get_low_stock_items()`: Intelligent query that identifies all inventory items below their reorder threshold.
- `create_requisition(material_id, quantity, requested_by)`: **WRITE TOOL**. Creates a new purchase requisition in a `pending_approval` state.
- `approve_pending_requisition(requisition_id, approved_by)`: **WRITE TOOL**. Approves a pending requisition. Must be explicitly triggered by human confirmation.

## Testing Locally

### Using the Custom Python Client

To prove that this server supports remote transport via HTTP (Server-Sent Events), you can use the built-in client script:

```bash
python client.py
```

### Using Claude Desktop (Stdio transport)

To test with Claude Desktop, configure your `claude_desktop_config.json` to use the `uv run` command:

```json
{
  "mcpServers": {
    "erp-lite": {
      "command": "C:\\Absolute\\Path\\To\\erp-lite-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "src.server"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": "C:\\Absolute\\Path\\To\\erp-lite-mcp"
      }
    }
  }
}
```

> **Note for Windows Users:** Claude Desktop runs in a sandboxed environment on Windows. Using `uv run` directly inside the config often fails to resolve relative module paths correctly. It is highly recommended to provide the absolute path to the `.venv\Scripts\python.exe` and explicitly pass your project directory as the `PYTHONPATH` environment variable as shown above.

## Running Unit Tests

To run the `pytest` suite testing the tool logic and requisition lifecycle:

```bash
uv run pytest
```

## Future Enhancements

- **Authentication & RBAC:** Implement Role-Based Access Control to ensure the `approved_by` identity has the actual rights to approve the specific value/material in the requisition.
- **Audit Logging:** Maintain a strict append-only audit trail of who/what queried and executed which tool, crucial for compliance (e.g. SOX).
- **Policy Search Resource:** A RAG-like capability to expose procurement policy documents to the agent as MCP resources.
