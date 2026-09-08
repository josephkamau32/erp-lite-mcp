import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db import SessionLocal, get_db
from src.models import Base, SalesOrder, InventoryItem, PurchaseRequisition, AuditLog
import src.tools.orders as orders
import src.tools.inventory as inventory
import src.tools.requisitions as requisitions
import src.server as server

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db(monkeypatch):
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Patch SessionLocal to use TestingSessionLocal
    monkeypatch.setattr("src.tools.orders.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.tools.inventory.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.tools.requisitions.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.server.SessionLocal", TestingSessionLocal)
    
    db = TestingSessionLocal()
    
    # Insert test data
    from datetime import date
    db.add(SalesOrder(order_id="SO-TEST-1", customer_name="Test Corp", status="open", order_date=date(2026, 8, 1), total_value=100.0))
    db.add(InventoryItem(material_id="MAT-TEST-1", description="Test Item", quantity_on_hand=50, reorder_point=100, warehouse="WH-1"))
    db.add(InventoryItem(material_id="MAT-TEST-2", description="Test Item 2", quantity_on_hand=200, reorder_point=100, warehouse="WH-1"))
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_get_open_orders():
    result = orders.get_open_sales_orders(status="open")
    assert len(result) == 1
    assert result[0].order_id == "SO-TEST-1"

def test_check_inventory_level():
    result = inventory.check_inventory_level("MAT-TEST-1")
    assert result.material_id == "MAT-TEST-1"
    assert result.below_reorder_point is True

def test_check_inventory_not_found():
    with pytest.raises(ValueError, match="Material MAT-UNKNOWN not found"):
        inventory.check_inventory_level("MAT-UNKNOWN")

def test_check_inventory():
    result = server.check_inventory("MAT-TEST-1")
    assert result.material_id == "MAT-TEST-1"
    assert result.quantity_on_hand == 50
    assert result.below_reorder_point is True

def test_list_low_stock_items():
    result = inventory.list_low_stock_items()
    assert len(result) == 1
    assert result[0].material_id == "MAT-TEST-1"

def test_get_low_stock_items():
    result = server.get_low_stock_items()
    assert len(result) == 1
    assert result[0].material_id == "MAT-TEST-1"

def test_requisition_lifecycle():
    # 1. Create requisition
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1", 
        quantity=100, 
        requested_by="Test User"
    )
    assert req.status == "pending_approval"
    assert req.material_id == "MAT-TEST-1"
    assert req.approved_at is None
    
    # fetch token from db
    db = TestingSessionLocal()
    db_req = db.query(PurchaseRequisition).filter(PurchaseRequisition.requisition_id == req.requisition_id).first()
    token = db_req.approval_token
    db.close()
    
    assert token is not None
    
    # 2. Approve requisition
    approved_req = requisitions.approve_requisition(
        requisition_id=req.requisition_id,
        approved_by="Test Manager",
        approval_token=token
    )
    assert approved_req.status == "approved"
    assert approved_req.approved_at is not None

def test_approve_with_wrong_token():
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1", 
        quantity=100, 
        requested_by="Test User"
    )
    
    with pytest.raises(ValueError, match="Invalid or missing approval token"):
        requisitions.approve_requisition(
            requisition_id=req.requisition_id,
            approved_by="Test Manager",
            approval_token="wrong_token_123"
        )

def test_approve_with_missing_token():
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1", 
        quantity=100, 
        requested_by="Test User"
    )
    
    with pytest.raises(ValueError, match="Invalid or missing approval token"):
        requisitions.approve_requisition(
            requisition_id=req.requisition_id,
            approved_by="Test Manager",
            approval_token=""
        )

def test_approve_already_approved_requisition():
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1", 
        quantity=100, 
        requested_by="Test User"
    )
    
    db = TestingSessionLocal()
    db_req = db.query(PurchaseRequisition).filter(PurchaseRequisition.requisition_id == req.requisition_id).first()
    token = db_req.approval_token
    db.close()
    
    requisitions.approve_requisition(
        requisition_id=req.requisition_id,
        approved_by="Test Manager",
        approval_token=token
    )
    
    with pytest.raises(ValueError, match="is already approved"):
        requisitions.approve_requisition(
            requisition_id=req.requisition_id,
            approved_by="Another Manager",
            approval_token=token
        )

def test_create_requisition_invalid_material():
    with pytest.raises(ValueError, match="Material MAT-INVALID not found"):
        requisitions.create_purchase_requisition("MAT-INVALID", 100, "Test User")

def test_create_requisition_invalid_quantity():
    with pytest.raises(ValueError, match="Quantity must be positive"):
        requisitions.create_purchase_requisition("MAT-TEST-1", -10, "Test User")

def test_approve_nonexistent_requisition():
    with pytest.raises(ValueError, match="Requisition PR-NONEXISTENT not found"):
        requisitions.approve_requisition("PR-NONEXISTENT", "Test Manager", "token")

def test_create_requisition():
    result = server.create_requisition(
        material_id="MAT-TEST-1",
        quantity=25,
        requested_by="Test User",
    )
    assert "Successfully created requisition" in result
    assert "MAT-TEST-1" in result
    assert "pending_approval" in result


# ---------------------------------------------------------------------------
# Audit log tests
# ---------------------------------------------------------------------------

def test_audit_log_records_tool_call():
    """Calling a tool via the server wrapper should create an audit log entry."""
    server.get_open_orders(status="open")

    db = TestingSessionLocal()
    entries = db.query(AuditLog).filter(AuditLog.tool_name == "get_open_orders").all()
    db.close()

    assert len(entries) >= 1
    latest = entries[-1]
    assert "open" in latest.arguments
    assert "Returned" in latest.result

def test_audit_log_redacts_approval_token():
    """The raw approval_token value must NEVER appear in audit_log.arguments."""
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1",
        quantity=100,
        requested_by="Test User",
    )

    db = TestingSessionLocal()
    db_req = db.query(PurchaseRequisition).filter(
        PurchaseRequisition.requisition_id == req.requisition_id
    ).first()
    real_token = db_req.approval_token
    db.close()

    # Approve via the server wrapper (which triggers audit logging)
    server.approve_pending_requisition(
        requisition_id=req.requisition_id,
        approved_by="Test Manager",
        approval_token=real_token,
    )

    db = TestingSessionLocal()
    entries = db.query(AuditLog).filter(
        AuditLog.tool_name == "approve_pending_requisition"
    ).all()
    db.close()

    assert len(entries) >= 1
    for entry in entries:
        # The raw token must not appear anywhere in the stored arguments
        assert real_token not in entry.arguments
        # The redaction placeholder must be present
        assert "***REDACTED***" in entry.arguments

def test_audit_log_records_failed_approval():
    """A failed approval attempt (wrong token) must still be logged."""
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1",
        quantity=100,
        requested_by="Test User",
    )

    with pytest.raises(ValueError):
        server.approve_pending_requisition(
            requisition_id=req.requisition_id,
            approved_by="Test Manager",
            approval_token="totally_wrong_token",
        )

    db = TestingSessionLocal()
    entries = db.query(AuditLog).filter(
        AuditLog.tool_name == "approve_pending_requisition"
    ).all()
    db.close()

    assert len(entries) >= 1
    failed_entry = entries[-1]
    assert "FAILED" in failed_entry.result
    # The wrong token value must also be redacted (it's still in _SENSITIVE_ARG_NAMES)
    assert "totally_wrong_token" not in failed_entry.arguments
    assert "***REDACTED***" in failed_entry.arguments

def test_redact_arguments_helper():
    """Unit test for the _redact_arguments function directly."""
    raw = {"requisition_id": "PR-123", "approved_by": "Alice", "approval_token": "secret_abc"}
    redacted = server._redact_arguments(raw)

    assert redacted["requisition_id"] == "PR-123"
    assert redacted["approved_by"] == "Alice"
    assert redacted["approval_token"] == "***REDACTED***"
    # Original dict must be untouched
    assert raw["approval_token"] == "secret_abc"

