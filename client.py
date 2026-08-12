import asyncio
import argparse
from mcp import ClientSession
from mcp.client.sse import sse_client

async def run(port: int):
    # Connect to the FastMCP SSE server
    url = f"http://localhost:{port}/sse"
    
    print(f"Connecting to {url}...")
    
    async with sse_client(url) as streams:
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
    parser.add_argument("--port", type=int, default=8000, help="Port of the SSE server")
    args = parser.parse_args()
    
    asyncio.run(run(args.port))
