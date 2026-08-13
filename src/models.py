from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    order_id = Column(String(50), primary_key=True)
    customer_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    order_date = Column(Date, nullable=False)
    total_value = Column(Numeric(10, 2), nullable=False)

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    material_id = Column(String(50), primary_key=True)
    description = Column(String(255), nullable=False)
    quantity_on_hand = Column(Integer, nullable=False)
    reorder_point = Column(Integer, nullable=False)
    warehouse = Column(String(50), nullable=False)

class PurchaseRequisition(Base):
    __tablename__ = 'purchase_requisitions'
    requisition_id = Column(String(50), primary_key=True)
    material_id = Column(String(50), ForeignKey('inventory_items.material_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    requested_by = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    approval_token = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    approved_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_name = Column(String(100), nullable=False)
    arguments = Column(String(2000), nullable=False)
    result = Column(String(2000), nullable=False)
    timestamp = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

