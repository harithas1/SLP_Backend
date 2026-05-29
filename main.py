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

from database import orders_collection, products_collection
from models.order import SaveOrderData, CartItem, Customer
from models.product import ProductCreate, ProductUpdate
from typing import List

from datetime import datetime, timezone
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
    items: List[CartItem]
    customer: Customer


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
        "exp": int(time.time()) + 60 * 60 * 24,
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
        created_at = order["createdAt"]

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        order["createdAt"] = created_at.isoformat().replace("+00:00", "Z")

    if "updatedAt" in order and isinstance(order["updatedAt"], datetime):
        updated_at = order["updatedAt"]

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        order["updatedAt"] = updated_at.isoformat().replace("+00:00", "Z")

    return order




def serialize_product(product):
    product["_id"] = str(product["_id"])

    if "createdAt" in product and isinstance(product["createdAt"], datetime):
        created_at = product["createdAt"]

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        product["createdAt"] = created_at.isoformat().replace("+00:00", "Z")

    if "updatedAt" in product and isinstance(product["updatedAt"], datetime):
        updated_at = product["updatedAt"]

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        product["updatedAt"] = updated_at.isoformat().replace("+00:00", "Z")

    return product


def calculate_cart_total(items: List[CartItem]):
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_amount = 0
    order_products = []

    for item in items:
        product = products_collection.find_one(
            {
                "id": item.productId,
                "isActive": {"$ne": False},
            }
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {item.productId}",
            )

        price = int(product.get("price", 0))
        postal = int(product.get("postal", 0))
        quantity = int(item.quantity)

        item_total = (price + postal) * quantity
        total_amount += item_total

        order_products.append(
            {
                "productId": int(product["id"]),
                "slug": product.get("slug", ""),
                "title": product.get("title", ""),
                "price": price,
                "postal": postal,
                "quantity": quantity,
                "image": product.get("image", ""),
                "itemTotal": item_total,
            }
        )

    return total_amount, order_products
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
            "message": "Admin username/password not configured in Railway",
        }

    username_ok = hmac.compare_digest(
        data.username.strip(),
        admin_username.strip(),
    )

    password_ok = hmac.compare_digest(
        data.password.strip(),
        admin_password.strip(),
    )

    if not username_ok or not password_ok:
        return {
            "success": False,
            "message": "Invalid username or password",
        }

    token = create_admin_token(data.username.strip())

    return {
        "success": True,
        "token": token,
        "message": "Admin login successful",
    }






# =========================
# PRODUCTS - PUBLIC GET
# =========================

@app.get("/products")
def get_products():
    try:
        products = list(
            products_collection.find(
                {
                    "isActive": {"$ne": False},
                    "id": {"$exists": True, "$ne": None},
                    "slug": {"$exists": True, "$nin": [None, "", "undefined"]},
                    "title": {"$exists": True, "$ne": ""},
                    "price": {"$exists": True, "$ne": None},
                }
            ).sort("id", 1)
        )

        return {
            "success": True,
            "products": [serialize_product(product) for product in products],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/products/{slug}")
def get_product_by_slug(slug: str):
    try:
        if not slug or slug in ["undefined", "null"]:
            return {
                "success": False,
                "message": "Product not found",
            }

        product = products_collection.find_one(
            {
                "slug": slug,
                "isActive": {"$ne": False},
            }
        )

        if not product:
            return {
                "success": False,
                "message": "Product not found",
            }

        return {
            "success": True,
            "product": serialize_product(product),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }



# =========================
# PRODUCTS - ADMIN
# =========================

@app.get("/admin/products")
def get_admin_products(admin=Depends(require_admin)):
    try:
        products = list(products_collection.find().sort("id", 1))

        return {
            "success": True,
            "products": [serialize_product(product) for product in products],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/products")
def create_product(
    data: ProductCreate,
    admin=Depends(require_admin),
):
    try:
        existing = products_collection.find_one(
            {
                "$or": [
                    {"id": data.id},
                    {"slug": data.slug},
                ]
            }
        )

        if existing:
            return {
                "success": False,
                "message": "Product ID or slug already exists",
            }

        now = datetime.now(timezone.utc)

        product_data = data.model_dump()
        product_data["createdAt"] = now
        product_data["updatedAt"] = now

        result = products_collection.insert_one(product_data)

        product = products_collection.find_one({"_id": result.inserted_id})

        return {
            "success": True,
            "message": "Product created successfully",
            "product": serialize_product(product),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdate,
    admin=Depends(require_admin),
):
    try:
        existing_product = products_collection.find_one({"id": product_id})

        if not existing_product:
            return {
                "success": False,
                "message": "Product not found",
            }

        update_data = data.model_dump(exclude_unset=True)
        if "slug" in update_data:
            slug_exists = products_collection.find_one(
                {
                    "slug": update_data["slug"],
                    "id": {"$ne": product_id},
                }
            )

            if slug_exists:
                return {
                    "success": False,
                    "message": "Slug already exists",
                }

        if not update_data:
            return {
                "success": False,
                "message": "No data provided to update",
            }

        update_data["updatedAt"] = datetime.now(timezone.utc)

        products_collection.update_one(
            {"id": product_id},
            {"$set": update_data},
        )

        product = products_collection.find_one({"id": product_id})

        return {
            "success": True,
            "message": "Product updated successfully",
            "product": serialize_product(product),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    admin=Depends(require_admin),
):
    try:
        result = products_collection.update_one(
            {"id": product_id},
            {
                "$set": {
                    "isActive": False,
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )

        if result.matched_count == 0:
            return {
                "success": False,
                "message": "Product not found",
            }

        return {
            "success": True,
            "message": "Product deleted successfully",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =========================
# CREATE RAZORPAY ORDER
# =========================



def get_razorpay_credentials():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=500,
            detail="Razorpay credentials are not configured",
        )

    return key_id, key_secret


def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    _, razorpay_secret = get_razorpay_credentials()

    body = f"{razorpay_order_id}|{razorpay_payment_id}"

    expected_signature = hmac.new(
        razorpay_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, razorpay_signature)



@app.post("/create-order")
def create_order(data: OrderData):
    try:
        razorpay_key_id = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
        razorpay_key_secret = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()

        if not razorpay_key_id or not razorpay_key_secret:
            return {
                "success": False,
                "message": "Razorpay live keys are not configured in Railway",
            }

        if not razorpay_key_id.startswith("rzp_live_"):
            return {
                "success": False,
                "message": "Backend is not using Razorpay live key",
            }

        total_amount, order_products = calculate_cart_total(data.items)
        amount_paise = total_amount * 100

        if amount_paise < 100:
            return {
                "success": False,
                "message": "Amount must be at least ₹1",
            }

        razorpay_client = razorpay.Client(
            auth=(razorpay_key_id, razorpay_key_secret)
        )

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": f"SLP-{int(time.time())}",
            "notes": {
                "source": "Lakshya Publications",
                "customer_name": data.customer.name[:256],
                "customer_phone": data.customer.phone[:256],
                "city": data.customer.city[:256],
                "state": data.customer.state[:256],
                "pincode": data.customer.pincode[:256],
                "product_ids": ",".join(
                    [str(product["productId"]) for product in order_products]
                )[:256],
            },
        }

        order = razorpay_client.order.create(data=order_data)  # type: ignore[attr-defined]

        return {
            "success": True,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": razorpay_key_id,
            "totalAmount": total_amount,
            "products": order_products,
        }

    except HTTPException:
        raise
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
        is_valid = verify_razorpay_signature(
            data.razorpay_order_id,
            data.razorpay_payment_id,
            data.razorpay_signature,
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature",
            )

        return {
            "success": True,
            "message": "Payment verified",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment verification failed: {str(e)}",
        )

# =========================
# SAVE ORDER
# PUBLIC
# =========================


@app.post("/save-order")
def save_order(data: SaveOrderData):
    try:
        is_valid = verify_razorpay_signature(
            data.razorpay_order_id,
            data.razorpay_payment_id,
            data.razorpay_signature,
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature. Order not saved.",
            )

        total_amount, order_products = calculate_cart_total(data.items)

        razorpay_key_id, razorpay_key_secret = get_razorpay_credentials()

        razorpay_client = razorpay.Client(
            auth=(razorpay_key_id, razorpay_key_secret)
        )

        razorpay_order = razorpay_client.order.fetch(data.razorpay_order_id)  # type: ignore[attr-defined]
        paid_order_amount = int(razorpay_order.get("amount", 0))

        if paid_order_amount != total_amount * 100:
            raise HTTPException(
                status_code=400,
                detail="Paid amount does not match backend product total.",
            )

        now = datetime.now(timezone.utc)

        order_data = {
            "customer":data.customer.model_dump(),
            "products": order_products,
            "totalAmount": total_amount,

            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,

            "paymentDetails": {
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature,
            },

            "paymentStatus": "Paid",
            "orderStatus": "Pending",
            "courierTrackingId": "",

            "createdAt": now,
            "updatedAt": now,
        }

        result = orders_collection.insert_one(order_data)

        return {
            "success": True,
            "message": "Order saved successfully",
            "order_id": str(result.inserted_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }



# =========================
# GET ORDERS
# ADMIN PROTECTED
# =========================

@app.get("/orders")
def get_orders(admin=Depends(require_admin)):
    try:
        orders = list(orders_collection.find().sort("createdAt", -1))
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
                    "updatedAt": datetime.now(timezone.utc),                }
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
# UPDATE COURIER TRACKING
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
                    "updatedAt": datetime.now(timezone.utc),                }
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
# PUBLIC
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