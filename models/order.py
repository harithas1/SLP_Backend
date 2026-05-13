from pydantic import BaseModel
from typing import List, Optional


class ProductItem(BaseModel):
    productId: int
    title: str
    price: int
    quantity: int
    image: Optional[str] = ""


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
    products: List[ProductItem]
    totalAmount: int

    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str