from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://srilakshyapublications.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Razorpay Client
client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET"),
    )
)

class OrderData(BaseModel):
    amount: int

@app.post("/create-order")
def create_order(data: OrderData):

    try:
        print("KEY ID:", os.getenv("RAZORPAY_KEY_ID"))
        print("KEY SECRET:", os.getenv("RAZORPAY_KEY_SECRET"))

        order = client.order.create({
            "amount": data.amount * 100,
            "currency": "INR",
            "payment_capture": 1
        })

        return {
            "success": True,
            "order_id": order["id"]
        }

    except Exception as e:
        print("RAZORPAY ERROR:", str(e))

        return {
            "success": False,
            "error": str(e)
        }








# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from routes import category, product, order
# import cloudinary
# import cloudinary.uploader
# from dotenv import load_dotenv
# import os
#
# load_dotenv()
#
# app = FastAPI()
#
# # ✅ FRONTEND URLS
# origins = [
#     "http://localhost:5173",
#     "https://srilakshyapublications.netlify.app"
# ]
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
#
# # ✅ CLOUDINARY
# cloudinary.config(
#     cloud_name=os.getenv("CLOUD_NAME"),
#     api_key=os.getenv("CLOUD_API_KEY"),
#     api_secret=os.getenv("CLOUD_API_SECRET"),
#     secure=True,
# )
#
# # ✅ ROUTES
# app.include_router(category.router)
# app.include_router(product.router)
# app.include_router(order.router)