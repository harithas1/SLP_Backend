from fastapi import APIRouter, HTTPException
from database import orders_collection
from models.order import Order

router = APIRouter()

@router.post("/orders")
def create_order(order: Order):

    if len(order.items) == 0:
        raise HTTPException(status_code=400, detail="Cart is empty")

    result = orders_collection.insert_one(order.dict())

    return {
        "message": "Order placed successfully",
        "order_id": str(result.inserted_id)
    }