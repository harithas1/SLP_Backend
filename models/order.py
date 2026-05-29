# models/order.py

from pydantic import BaseModel, Field
from typing import List, Optional


class CartItem(BaseModel):
    productId: int
    quantity: int = Field(..., ge=1, le=50)


class Customer(BaseModel):
    name: str
    relationType: str
    relationName: str
    fullAddress: str
    city: str
    state: str
    pincode: str
    phone: str
    email: Optional[str] = ""
    notes: Optional[str] = ""


class SaveOrderData(BaseModel):
    customer: Customer
    items: List[CartItem]

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str