import os
from mcp.server.fastmcp import FastMCP
from typing import List, Optional

# Import tools
from .tools.orders import get_open_sales_orders
from .tools.inventory import check_inventory_level, list_low_stock_items
from .tools.requisitions import create_purchase_requisition, approve_requisition
from .schemas import SalesOrderResponse, InventoryCheckResponse, PurchaseRequisitionResponse

# Create FastMCP server
mcp = FastMCP("erp-lite", host="0.0.0.0")

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

from starlette.requests import Request
from starlette.responses import JSONResponse
from .db import SessionLocal
from .models import PurchaseRequisition

@mcp.tool()
def create_requisition(material_id: str, quantity: int, requested_by: str) -> str:
    """
    Create a new purchase requisition (pending approval).
    The agent CANNOT approve its own requisition.
    """
    req = create_purchase_requisition(material_id, quantity, requested_by)
    return f"Successfully created requisition {req.requisition_id} for {quantity} units of {material_id}. Status: {req.status}."

@mcp.tool()
def approve_pending_requisition(requisition_id: str, approved_by: str, approval_token: str) -> str:
    """
    Approve a pending purchase requisition. 
    This MUST be triggered by a human via approval mechanisms.
    The required approval_token is only accessible to human administrators.
    """
    req = approve_requisition(requisition_id, approved_by, approval_token)
    return f"Successfully approved requisition {req.requisition_id}. Status is now {req.status}."

@mcp.custom_route("/admin/pending-requisitions", methods=["GET"])
async def list_pending_requisitions(request: Request):
    """
    Admin-only endpoint to view pending requisitions and their approval tokens.
    """
    admin_key = os.environ.get("ADMIN_API_KEY")
    if not admin_key:
        return JSONResponse({"error": "Server configuration error: ADMIN_API_KEY not set"}, status_code=500)
        
    client_key = request.headers.get("X-Admin-Key")
    if not client_key or client_key != admin_key:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
    with SessionLocal() as db:
        pending = db.query(PurchaseRequisition).filter(PurchaseRequisition.status == "pending_approval").all()
        results = [
            {
                "requisition_id": r.requisition_id,
                "material_id": r.material_id,
                "quantity": r.quantity,
                "requested_by": r.requested_by,
                "approval_token": r.approval_token
            }
            for r in pending
        ]
        
    return JSONResponse({"pending_requisitions": results})

# When run directly, we use stdio by default or check arguments for HTTP setup
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "streamable-http":
        print("Starting Streamable HTTP server...")
        # Start Streamable HTTP transport using FastMCP's built in run command
        mcp.run(transport="streamable-http")
    else:
        # Default to stdio transport for Claude Desktop
        mcp.run()
