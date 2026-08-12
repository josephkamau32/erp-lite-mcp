import asyncio
from src.server import mcp

async def test():
    req = await mcp.call_tool('create_requisition', {'material_id': 'MAT-004', 'quantity': 100, 'requested_by': 'Test'})
    print(req)

asyncio.run(test())
