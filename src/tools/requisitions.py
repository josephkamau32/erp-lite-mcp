import uuid
import secrets
from datetime import datetime
from ..db import SessionLocal
from ..models import PurchaseRequisition, InventoryItem
from ..schemas import PurchaseRequisitionResponse

def create_purchase_requisition(material_id: str, quantity: int, requested_by: str) -> PurchaseRequisitionResponse:
    """
    Create a new purchase requisition. It will be created with status 'pending_approval'.
    The agent CANNOT approve its own requisition.
    
    Args:
        material_id: The ID of the material to requisition.
        quantity: The quantity to requisition.
        requested_by: The name of the person requesting the requisition.
    """
    with SessionLocal() as db:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
            
        # Validate material exists
        item = db.query(InventoryItem).filter(InventoryItem.material_id == material_id).first()
        if not item:
            raise ValueError(f"Material {material_id} not found. Cannot create requisition.")
            
        requisition_id = f"PR-{uuid.uuid4().hex[:6].upper()}"
        approval_token = secrets.token_urlsafe(16)
        
        new_req = PurchaseRequisition(
            requisition_id=requisition_id,
            material_id=material_id,
            quantity=quantity,
            requested_by=requested_by,
            status="pending_approval",
            approval_token=approval_token
        )
        db.add(new_req)
        db.commit()
        db.refresh(new_req)
        
        return PurchaseRequisitionResponse.model_validate(new_req)

def approve_requisition(requisition_id: str, approved_by: str, approval_token: str) -> PurchaseRequisitionResponse:
    """
    Approve a pending purchase requisition.
    This action MUST be triggered by a human via approval mechanisms.
    
    Args:
        requisition_id: The ID of the requisition to approve.
        approved_by: The name of the human approving the requisition.
        approval_token: The token required to approve the requisition.
    """
    with SessionLocal() as db:
        req = db.query(PurchaseRequisition).filter(PurchaseRequisition.requisition_id == requisition_id).first()
        if not req:
            raise ValueError(f"Requisition {requisition_id} not found.")
            
        if req.status == "approved":
            raise ValueError(f"Requisition {requisition_id} is already approved.")
            
        if not req.approval_token or not approval_token or not secrets.compare_digest(req.approval_token, approval_token):
            raise ValueError(f"Invalid or missing approval token for requisition {requisition_id}.")
            
        req.status = "approved"
        req.approved_at = datetime.utcnow()
        db.commit()
        db.refresh(req)
        
        return PurchaseRequisitionResponse.model_validate(req)
