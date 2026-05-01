from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import category, product, order
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
    secure=True
)
app.include_router(category.router)
app.include_router(product.router)
app.include_router(order.router)