import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db import SessionLocal, get_db
from src.models import Base, SalesOrder, InventoryItem, PurchaseRequisition
import src.tools.orders as orders
import src.tools.inventory as inventory
import src.tools.requisitions as requisitions

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

def test_list_low_stock_items():
    result = inventory.list_low_stock_items()
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
    
    # 2. Approve requisition
    approved_req = requisitions.approve_requisition(
        requisition_id=req.requisition_id,
        approved_by="Test Manager"
    )
    assert approved_req.status == "approved"
    assert approved_req.approved_at is not None

def test_approve_already_approved_requisition():
    req = requisitions.create_purchase_requisition(
        material_id="MAT-TEST-1", 
        quantity=100, 
        requested_by="Test User"
    )
    requisitions.approve_requisition(
        requisition_id=req.requisition_id,
        approved_by="Test Manager"
    )
    
    with pytest.raises(ValueError, match="is already approved"):
        requisitions.approve_requisition(
            requisition_id=req.requisition_id,
            approved_by="Another Manager"
        )
