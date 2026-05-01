from pydantic import BaseModel, EmailStr, Field
from typing import List

class OrderItem(BaseModel):
    product_id: str
    quantity: int

class Order(BaseModel):
    full_name: str = Field(..., min_length=3)
    phone: str = Field(..., min_length=10, max_length=10)
    email: EmailStr
    address: str
    city: str
    state: str
    pincode: str

    items: List[OrderItem]
    total: int