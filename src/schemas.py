from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime

class SalesOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    order_id: str
    customer_name: str
    status: str
    order_date: date
    total_value: float

class InventoryCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    material_id: str
    description: str
    quantity_on_hand: int
    reorder_point: int
    warehouse: str
    below_reorder_point: bool

class PurchaseRequisitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    requisition_id: str
    material_id: str
    quantity: int
    requested_by: str
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
