
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import razorpay
import os
import hmac
import hashlib

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://srilakshyapublications.netlify.app",
        "https://phh.support",
        "https://www.phh.support"
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

# =========================
# CREATE ORDER
# =========================

class OrderData(BaseModel):
    amount: int

@app.post("/create-order")
def create_order(data: OrderData):

    try:
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
        return {
            "success": False,
            "error": str(e)
        }

# =========================
# VERIFY PAYMENT
# =========================

class VerifyData(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@app.post("/verify-payment")
def verify_payment(data: VerifyData):

    try:
        body = (
            data.razorpay_order_id
            + "|"
            + data.razorpay_payment_id
        )

        expected_signature = hmac.new(
            bytes(os.getenv("RAZORPAY_KEY_SECRET"), "utf-8"),
            bytes(body, "utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if expected_signature == data.razorpay_signature:
            return {
                "success": True,
                "message": "Payment verified"
            }

        return {
            "success": False,
            "message": "Invalid signature"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }