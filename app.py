from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

import razorpay
import os
import hmac
import hashlib
import json
import time
import base64

from database import orders_collection
from models.order import SaveOrderData

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# =========================
# CORS
# =========================

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

# =========================
# RAZORPAY CLIENT
# =========================

client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET"),
    )
)

# =========================
# MODELS
# =========================

class OrderData(BaseModel):
    amount: int


class VerifyData(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class TrackOrderData(BaseModel):
    order_id: str
    phone: str


class UpdateStatusData(BaseModel):
    order_id: str
    orderStatus: str


class AdminLoginData(BaseModel):
    username: str
    password: str


class CourierTrackingData(BaseModel):
    order_id: str
    courierTrackingId: str = ""


# =========================
# ADMIN AUTH HELPERS
# =========================

def base64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def base64_url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_admin_token(username: str) -> str:
    secret = os.getenv("ADMIN_SECRET_KEY")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_SECRET_KEY is not configured",
        )

    payload = {
        "username": username,
        "exp": int(time.time()) + 60 * 60 * 24,  # 24 hours
    }

    payload_json = json.dumps(payload).encode()
    payload_base64 = base64_url_encode(payload_json)

    signature = hmac.new(
        secret.encode(),
        payload_base64.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload_base64}.{signature}"


def verify_admin_token(token: str):
    secret = os.getenv("ADMIN_SECRET_KEY")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_SECRET_KEY is not configured",
        )

    try:
        payload_base64, signature = token.split(".")

        expected_signature = hmac.new(
            secret.encode(),
            payload_base64.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid admin token")

        payload = json.loads(base64_url_decode(payload_base64))

        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=401, detail="Admin token expired")

        return payload

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def require_admin(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "").strip()

    return verify_admin_token(token)


# =========================
# HELPERS
# =========================

def get_order_filter(order_id: str):
    try:
        return {"_id": ObjectId(order_id)}
    except Exception:
        return {"_id": order_id}


def serialize_order(order):
    order["_id"] = str(order["_id"])

    if "createdAt" in order and isinstance(order["createdAt"], datetime):
        order["createdAt"] = order["createdAt"].isoformat()

    if "updatedAt" in order and isinstance(order["updatedAt"], datetime):
        order["updatedAt"] = order["updatedAt"].isoformat()

    return order


# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# ADMIN LOGIN
# =========================

@app.post("/admin-login")
def admin_login(data: AdminLoginData):
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        return {
            "success": False,
            "message": "Admin username or password is not configured in backend",
        }

    username_ok = hmac.compare_digest(data.username, admin_username)
    password_ok = hmac.compare_digest(data.password, admin_password)

    if not username_ok or not password_ok:
        return {
            "success": False,
            "message": "Invalid username or password",
        }

    token = create_admin_token(data.username)

    return {
        "success": True,
        "token": token,
        "message": "Admin login successful",
    }


# =========================
# CREATE RAZORPAY ORDER
# =========================

@app.post("/create-order")
def create_order(data: OrderData):
    try:
        order = client.order.create(
            {
                "amount": data.amount * 100,
                "currency": "INR",
                "payment_capture": 1,
            }
        )

        return {
            "success": True,
            "order_id": order["id"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# VERIFY PAYMENT
# =========================

@app.post("/verify-payment")
def verify_payment(data: VerifyData):
    try:
        razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not razorpay_secret:
            return {
                "success": False,
                "message": "Razorpay secret is not configured",
            }

        body = data.razorpay_order_id + "|" + data.razorpay_payment_id

        expected_signature = hmac.new(
            bytes(razorpay_secret, "utf-8"),
            bytes(body, "utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(expected_signature, data.razorpay_signature):
            return {
                "success": True,
                "message": "Payment verified",
            }

        return {
            "success": False,
            "message": "Invalid signature",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# SAVE ORDER
# PUBLIC ROUTE
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

            # top-level fields for admin invoice compatibility
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,

            # nested payment details also kept
            "paymentDetails": {
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
            },

            "paymentStatus": "Paid",
            "orderStatus": "Pending",
            "courierTrackingId": "",

            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        result = orders_collection.insert_one(order_data)

        return {
            "success": True,
            "message": "Order saved successfully",
            "order_id": str(result.inserted_id),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# GET ALL ORDERS
# ADMIN PROTECTED
# =========================

@app.get("/orders")
def get_orders(admin=Depends(require_admin)):
    try:
        orders = list(
            orders_collection.find().sort("createdAt", -1)
        )

        orders = [serialize_order(order) for order in orders]

        return {
            "success": True,
            "orders": orders,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# UPDATE ORDER STATUS
# ADMIN PROTECTED
# =========================

@app.put("/update-order-status")
def update_order_status(
    data: UpdateStatusData,
    admin=Depends(require_admin),
):
    try:
        allowed_statuses = [
            "Pending",
            "Confirmed",
            "Packed",
            "Shipped",
            "Delivered",
            "Cancelled",
        ]

        if data.orderStatus not in allowed_statuses:
            return {
                "success": False,
                "message": "Invalid order status",
            }

        result = orders_collection.update_one(
            get_order_filter(data.order_id),
            {
                "$set": {
                    "orderStatus": data.orderStatus,
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

        if result.matched_count == 0:
            return {
                "success": False,
                "message": "Order not found",
            }

        return {
            "success": True,
            "message": "Status updated successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# UPDATE COURIER TRACKING ID
# ADMIN PROTECTED
# =========================

@app.put("/update-courier-tracking")
def update_courier_tracking(
    data: CourierTrackingData,
    admin=Depends(require_admin),
):
    try:
        result = orders_collection.update_one(
            get_order_filter(data.order_id),
            {
                "$set": {
                    "courierTrackingId": data.courierTrackingId.strip(),
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

        if result.matched_count == 0:
            return {
                "success": False,
                "message": "Order not found",
            }

        return {
            "success": True,
            "message": "Courier tracking ID updated successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================
# TRACK ORDER
# PUBLIC ROUTE
# =========================

@app.post("/track-order")
def track_order(data: TrackOrderData):
    try:
        try:
            order_object_id = ObjectId(data.order_id)
        except Exception:
            return {
                "success": False,
                "message": "Invalid Order ID",
            }

        order = orders_collection.find_one(
            {
                "_id": order_object_id,
                "customer.phone": data.phone,
            }
        )

        if not order:
            return {
                "success": False,
                "message": "Order not found",
            }

        order = serialize_order(order)

        return {
            "success": True,
            "order": order,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }