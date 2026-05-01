from pydantic import BaseModel

class Product(BaseModel):
    title: str
    price: int
    image: str
    category: str
