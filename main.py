
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import razorpay
import os
import hmac
import hashlib
from database import orders_collection
from models.order import SaveOrderData

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://srilakshyapublications.netlify.app",
        "https://srilakshyapublications.in",
        "https://www.srilakshyapublications.in",
        "http://srilakshyapublications.in",
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


# =========================
# SAVE ORDER
# =========================

@app.post("/save-order")
def save_order(data: SaveOrderData):

    try:

        order_data = {
            "customer": data.customer.dict(),

            "products": [
                product.dict()
                for product in data.products
            ],

            "totalAmount": data.totalAmount,

            "paymentDetails": {
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
            },

            "paymentStatus": "Paid",

            "orderStatus": "Pending",

            "createdAt": datetime.utcnow()
        }

        result = orders_collection.insert_one(order_data)

        return {
            "success": True,
            "message": "Order saved successfully",
            "order_id": str(result.inserted_id)
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }



@app.get("/orders")
def get_orders():

    try:

        orders = list(
            orders_collection.find().sort("createdAt", -1)
        )

        for order in orders:
            order["_id"] = str(order["_id"])

        return {
            "success": True,
            "orders": orders
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

class UpdateStatusData(BaseModel):
    order_id: str
    orderStatus: str

@app.put("/update-order-status")
def update_order_status(data: UpdateStatusData):

    try:

        from bson import ObjectId

        orders_collection.update_one(
            {"_id": ObjectId(data.order_id)},
            {
                "$set": {
                    "orderStatus": data.orderStatus
                }
            }
        )

        return {
            "success": True,
            "message": "Status updated"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }








class TrackOrderData(BaseModel):
    order_id: str
    phone: str


@app.post("/track-order")
def track_order(data: TrackOrderData):

    try:

        order = orders_collection.find_one({
            "_id": ObjectId(data.order_id),
            "customer.phone": data.phone
        })

        if not order:
            return {
                "success": False,
                "message": "Order not found"
            }

        order["_id"] = str(order["_id"])

        return {
            "success": True,
            "order": order
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }