import os
import sys
import asyncio
import argparse
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def run(port: int, api_key: str | None = None):
    # Connect to the FastMCP server
    url = f"http://localhost:{port}/mcp"
    
    key = api_key or os.environ.get("MCP_API_KEY")
    if not key:
        print("Warning: MCP_API_KEY is not set. Requests to /mcp will likely be rejected.", file=sys.stderr)
        
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    
    print(f"Connecting to {url}...")
    
    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                print("Connected!")
                
                # Initialize connection
                await session.initialize()
                print("Session initialized.")
                
                # List available tools
                tools = await session.list_tools()
                print("\nAvailable Tools:")
                for tool in tools.tools:
                    print(f"- {tool.name}: {tool.description}")
                
                # Call a tool: get_open_orders
                print("\nCalling tool: get_open_orders")
                result = await session.call_tool("get_open_orders", {"status": "open", "limit": 5})
                print(f"Result:\n{result}")
                
                # 3. Create Requisition
                print("\nCalling tool: create_requisition (MAT-002, 50, 'System Test')")
                try:
                    req_result = await session.call_tool("create_requisition", arguments={
                        "material_id": "MAT-002",
                        "quantity": 50,
                        "requested_by": "System Test"
                    })
                    print("Result:", req_result.content[0].text)
                except Exception as e:
                    print("Error calling tool:", e)
                
                # Call a tool: check_inventory for MAT-002
                print("\nCalling tool: check_inventory (MAT-002)")
                result = await session.call_tool("check_inventory", {"material_id": "MAT-002"})
                print(f"Result:\n{result}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP Client")
    parser.add_argument("--port", type=int, default=8000, help="Port of the server")
    parser.add_argument("--api-key", type=str, default=None, help="MCP API key (defaults to MCP_API_KEY env var)")
    args = parser.parse_args()
    
    asyncio.run(run(args.port, args.api_key))
