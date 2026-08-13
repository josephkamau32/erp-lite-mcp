import os
import sys
import json
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from typing import List, Optional

# Import tools
from .tools.orders import get_open_sales_orders
from .tools.inventory import check_inventory_level, list_low_stock_items
from .tools.requisitions import create_purchase_requisition, approve_requisition
from .schemas import SalesOrderResponse, InventoryCheckResponse, PurchaseRequisitionResponse, AuditLogEntry
from .db import SessionLocal
from .models import PurchaseRequisition, AuditLog

from starlette.requests import Request
from starlette.responses import JSONResponse

# Create FastMCP server
mcp = FastMCP("erp-lite", host="0.0.0.0")

# ---------------------------------------------------------------------------
# Audit logging helpers
# ---------------------------------------------------------------------------

# Argument names whose values must never be persisted in plaintext.
_SENSITIVE_ARG_NAMES = {"approval_token"}

def _redact_arguments(arguments: dict) -> dict:
    """Return a copy of *arguments* with sensitive values replaced."""
    redacted = {}
    for key, value in arguments.items():
        if key in _SENSITIVE_ARG_NAMES:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted

def _record_audit(tool_name: str, arguments: dict, result: str) -> None:
    """Persist an append-only audit log entry.

    Arguments are redacted of sensitive values before serialization.
    This function is intentionally fire-and-forget; it should never
    prevent the caller from returning a tool result.
    """
    safe_args = json.dumps(_redact_arguments(arguments))
    try:
        with SessionLocal() as db:
            entry = AuditLog(
                tool_name=tool_name,
                arguments=safe_args,
                result=str(result)[:2000],
                timestamp=datetime.utcnow(),
            )
            db.add(entry)
            db.commit()
    except Exception as exc:
        # Fire-and-forget: never break a tool response, but surface the
        # failure in server logs so a broken audit table doesn't go unnoticed.
        print(f"[audit] failed to record entry: {exc}", file=sys.stderr)

# ---------------------------------------------------------------------------
# MCP Tools (with audit logging on both success and failure paths)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_open_orders(status: str = "open", limit: int = 20) -> List[SalesOrderResponse]:
    """Retrieve a list of sales orders by status."""
    args = {"status": status, "limit": limit}
    try:
        result = get_open_sales_orders(status, limit)
        _record_audit("get_open_orders", args, f"Returned {len(result)} orders")
        return result
    except Exception as exc:
        _record_audit("get_open_orders", args, f"FAILED: {exc}")
        raise

@mcp.tool()
def check_inventory(material_id: str) -> InventoryCheckResponse:
    """Check the inventory level for a specific material ID."""
    args = {"material_id": material_id}
    try:
        result = check_inventory_level(material_id)
        _record_audit("check_inventory", args, f"Found {material_id}, qty={result.quantity_on_hand}")
        return result
    except Exception as exc:
        _record_audit("check_inventory", args, f"FAILED: {exc}")
        raise

@mcp.tool()
def get_low_stock_items() -> List[InventoryCheckResponse]:
    """List all inventory items where the quantity on hand is below the reorder point."""
    args = {}
    try:
        result = list_low_stock_items()
        _record_audit("get_low_stock_items", args, f"Returned {len(result)} low-stock items")
        return result
    except Exception as exc:
        _record_audit("get_low_stock_items", args, f"FAILED: {exc}")
        raise



@mcp.tool()
def create_requisition(material_id: str, quantity: int, requested_by: str) -> str:
    """
    Create a new purchase requisition (pending approval).
    The agent CANNOT approve its own requisition.
    """
    args = {"material_id": material_id, "quantity": quantity, "requested_by": requested_by}
    try:
        req = create_purchase_requisition(material_id, quantity, requested_by)
        result_msg = f"Successfully created requisition {req.requisition_id} for {quantity} units of {material_id}. Status: {req.status}."
        _record_audit("create_requisition", args, result_msg)
        return result_msg
    except Exception as exc:
        _record_audit("create_requisition", args, f"FAILED: {exc}")
        raise

@mcp.tool()
def approve_pending_requisition(requisition_id: str, approved_by: str, approval_token: str) -> str:
    """
    Approve a pending purchase requisition. 
    This MUST be triggered by a human via approval mechanisms.
    The required approval_token is only accessible to human administrators.
    """
    args = {"requisition_id": requisition_id, "approved_by": approved_by, "approval_token": approval_token}
    try:
        req = approve_requisition(requisition_id, approved_by, approval_token)
        result_msg = f"Successfully approved requisition {req.requisition_id}. Status is now {req.status}."
        _record_audit("approve_pending_requisition", args, result_msg)
        return result_msg
    except Exception as exc:
        _record_audit("approve_pending_requisition", args, f"FAILED: {exc}")
        raise

# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

def _check_admin_auth(request: Request):
    """Validate X-Admin-Key header. Returns an error response or None."""
    admin_key = os.environ.get("ADMIN_API_KEY")
    if not admin_key:
        return JSONResponse({"error": "Server configuration error: ADMIN_API_KEY not set"}, status_code=500)
    client_key = request.headers.get("X-Admin-Key")
    if not client_key or client_key != admin_key:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return None

@mcp.custom_route("/admin/pending-requisitions", methods=["GET"])
async def list_pending_requisitions(request: Request):
    """
    Admin-only endpoint to view pending requisitions and their approval tokens.
    """
    auth_error = _check_admin_auth(request)
    if auth_error:
        return auth_error
        
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

@mcp.custom_route("/admin/audit-log", methods=["GET"])
async def get_audit_log(request: Request):
    """
    Admin-only endpoint to view the append-only audit trail.
    Supports ?limit=N (default 50, most recent first).
    """
    auth_error = _check_admin_auth(request)
    if auth_error:
        return auth_error

    try:
        limit = int(request.query_params.get("limit", "50"))
        limit = max(1, min(limit, 500))  # clamp between 1 and 500
    except (ValueError, TypeError):
        limit = 50

    with SessionLocal() as db:
        entries = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        results = [
            {
                "id": e.id,
                "tool_name": e.tool_name,
                "arguments": e.arguments,
                "result": e.result,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in entries
        ]

    return JSONResponse({"audit_log": results, "count": len(results), "limit": limit})

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
