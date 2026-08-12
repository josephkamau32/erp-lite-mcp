from typing import List
from ..db import SessionLocal
from ..models import SalesOrder
from ..schemas import SalesOrderResponse

def get_open_sales_orders(status: str = "open", limit: int = 20) -> List[SalesOrderResponse]:
    """
    Get a list of sales orders by status.
    
    Args:
        status: The status of the orders to retrieve (default: "open").
        limit: The maximum number of orders to retrieve (default: 20).
    """
    with SessionLocal() as db:
        orders = db.query(SalesOrder).filter(SalesOrder.status == status).limit(limit).all()
        # Ensure Decimal is cast to float for pydantic, though pydantic might handle it
        return [SalesOrderResponse.model_validate(order) for order in orders]
