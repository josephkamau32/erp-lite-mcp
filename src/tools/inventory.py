from typing import List
from ..db import SessionLocal
from ..models import InventoryItem
from ..schemas import InventoryCheckResponse

def check_inventory_level(material_id: str) -> InventoryCheckResponse:
    """
    Check the inventory level for a specific material.
    
    Args:
        material_id: The ID of the material to check.
    """
    with SessionLocal() as db:
        item = db.query(InventoryItem).filter(InventoryItem.material_id == material_id).first()
        if not item:
            raise ValueError(f"Material {material_id} not found")
            
        return InventoryCheckResponse(
            material_id=item.material_id,
            description=item.description,
            quantity_on_hand=item.quantity_on_hand,
            reorder_point=item.reorder_point,
            warehouse=item.warehouse,
            below_reorder_point=item.quantity_on_hand < item.reorder_point
        )

def list_low_stock_items() -> List[InventoryCheckResponse]:
    """
    List all inventory items where the quantity on hand is below the reorder point.
    """
    with SessionLocal() as db:
        items = db.query(InventoryItem).filter(InventoryItem.quantity_on_hand < InventoryItem.reorder_point).all()
        return [
            InventoryCheckResponse(
                material_id=item.material_id,
                description=item.description,
                quantity_on_hand=item.quantity_on_hand,
                reorder_point=item.reorder_point,
                warehouse=item.warehouse,
                below_reorder_point=True
            ) for item in items
        ]
