from pydantic import BaseModel

class Category(BaseModel):
    name: str
    image: str   # store image URL



    