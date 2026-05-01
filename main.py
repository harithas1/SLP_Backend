from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import category, product, order
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# ✅ FRONTEND URLS
origins = [
    "http://localhost:5173",
    "https://srilakshyapublications.netlify.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ CLOUDINARY
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
    secure=True,
)

# ✅ ROUTES
app.include_router(category.router)
app.include_router(product.router)
app.include_router(order.router)