# models/product.py

from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    price: int = Field(..., ge=1)
    oldPrice: int = Field(0, ge=0)
    discount: int = Field(0, ge=0)
    postal: int = Field(0, ge=0)
    description: str
    image: str
    isActive: bool = True


class ProductUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = Field(None, ge=1)
    oldPrice: Optional[int] = Field(None, ge=0)
    discount: Optional[int] = Field(None, ge=0)
    postal: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    image: Optional[str] = None
    isActive: Optional[bool] = None