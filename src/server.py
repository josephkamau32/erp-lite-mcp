import os
from mcp.server.fastmcp import FastMCP
from typing import List, Optional

# Import tools
from .tools.orders import get_open_sales_orders
from .tools.inventory import check_inventory_level, list_low_stock_items
from .tools.requisitions import create_purchase_requisition, approve_requisition
from .schemas import SalesOrderResponse, InventoryCheckResponse, PurchaseRequisitionResponse

# Create FastMCP server
mcp = FastMCP("erp-lite")

@mcp.tool()
def get_open_orders(status: str = "open", limit: int = 20) -> List[SalesOrderResponse]:
    """Retrieve a list of sales orders by status."""
    return get_open_sales_orders(status, limit)

@mcp.tool()
def check_inventory(material_id: str) -> InventoryCheckResponse:
    """Check the inventory level for a specific material ID."""
    return check_inventory_level(material_id)

@mcp.tool()
def get_low_stock_items() -> List[InventoryCheckResponse]:
    """List all inventory items where the quantity on hand is below the reorder point."""
    return list_low_stock_items()

@mcp.tool()
def create_requisition(material_id: str, quantity: int, requested_by: str) -> str:
    """
    Create a new purchase requisition (pending approval).
    The agent CANNOT approve its own requisition.
    """
    req = create_purchase_requisition(material_id, quantity, requested_by)
    return f"Successfully created requisition {req.requisition_id} for {quantity} units of {material_id}. Status: {req.status}."

@mcp.tool()
def approve_pending_requisition(requisition_id: str, approved_by: str) -> str:
    """
    Approve a pending purchase requisition. 
    This MUST be triggered by a human.
    """
    req = approve_requisition(requisition_id, approved_by)
    return f"Successfully approved requisition {req.requisition_id}. Status is now {req.status}."

# When run directly, we use stdio by default or check arguments for SSE setup
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        print("Starting SSE server on port 8000...")
        # Start SSE transport using FastMCP's built in run command
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    else:
        # Default to stdio transport for Claude Desktop
        mcp.run()
