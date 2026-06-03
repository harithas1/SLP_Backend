# models/order.py

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def clean_text(value):
    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value


def normalize_indian_phone(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))

    # Example: 09390810513 -> 9390810513
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Example: 919390810513 -> 9390810513
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10 digit Indian mobile number.")

    return digits


class CartItem(BaseModel):
    productId: int = Field(..., gt=0)
    quantity: int = Field(..., ge=1, le=50)


class Customer(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    relationType: str = Field(..., min_length=2, max_length=10)
    relationName: str = Field(..., min_length=2, max_length=80)
    fullAddress: str = Field(..., min_length=10, max_length=350)
    city: str = Field(..., min_length=2, max_length=80)
    state: str = Field(..., min_length=2, max_length=80)
    pincode: str = Field(..., min_length=6, max_length=6)
    phone: str = Field(..., min_length=10, max_length=10)
    email: Optional[str] = Field(default="", max_length=120)
    notes: Optional[str] = Field(default="", max_length=300)

    @field_validator(
        "name",
        "relationType",
        "relationName",
        "fullAddress",
        "city",
        "state",
        "pincode",
        "phone",
        "email",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_and_clean(cls, value):
        return clean_text(value)

    @field_validator("name", "relationName")
    @classmethod
    def validate_person_name(cls, value):
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Name must contain letters.")

        if re.search(r"[<>]", value):
            raise ValueError("Name contains invalid characters.")

        return value

    @field_validator("relationType")
    @classmethod
    def validate_relation_type(cls, value):
        allowed = {
            "S/o": "S/o",
            "D/o": "D/o",
            "W/o": "W/o",
            "C/o": "C/o",
            "s/o": "S/o",
            "d/o": "D/o",
            "w/o": "W/o",
            "c/o": "C/o",
        }

        if value not in allowed:
            raise ValueError("Relation type must be S/o, D/o, W/o or C/o.")

        return allowed[value]

    @field_validator("fullAddress")
    @classmethod
    def validate_full_address(cls, value):
        if len(value) < 10:
            raise ValueError("Full address is too short.")

        if len(value) > 350:
            raise ValueError("Full address is too long.")

        if re.search(r"[<>]", value):
            raise ValueError("Address contains invalid characters.")

        if not re.search(r"[A-Za-z0-9]", value):
            raise ValueError("Address must contain valid text.")

        return value

    @field_validator("city", "state")
    @classmethod
    def validate_place(cls, value):
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("City and state must contain letters.")

        if re.search(r"[<>]", value):
            raise ValueError("City or state contains invalid characters.")

        return value

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value):
        digits = re.sub(r"\D", "", value)

        if not re.fullmatch(r"[1-9]\d{5}", digits):
            raise ValueError("Enter a valid 6 digit Indian pincode.")

        return digits

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        return normalize_indian_phone(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if not value:
            return ""

        value = value.lower()

        if not re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", value):
            raise ValueError("Enter a valid email address.")

        return value

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value):
        if not value:
            return ""

        if re.search(r"[<>]", value):
            raise ValueError("Notes contain invalid characters.")

        return value


class SaveOrderData(BaseModel):
    customer: Customer
    items: List[CartItem] = Field(..., min_length=1, max_length=20)

    razorpay_order_id: str = Field(..., min_length=5, max_length=100)
    razorpay_payment_id: str = Field(..., min_length=5, max_length=100)
    razorpay_signature: str = Field(..., min_length=64, max_length=64)

    @field_validator(
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        mode="before",
    )
    @classmethod
    def clean_payment_fields(cls, value):
        return clean_text(value)

    @field_validator("razorpay_order_id")
    @classmethod
    def validate_razorpay_order_id(cls, value):
        if not value.startswith("order_"):
            raise ValueError("Invalid Razorpay order ID.")

        return value

    @field_validator("razorpay_payment_id")
    @classmethod
    def validate_razorpay_payment_id(cls, value):
        if not value.startswith("pay_"):
            raise ValueError("Invalid Razorpay payment ID.")

        return value

    @field_validator("razorpay_signature")
    @classmethod
    def validate_razorpay_signature(cls, value):
        if not re.fullmatch(r"[a-fA-F0-9]{64}", value):
            raise ValueError("Invalid Razorpay signature.")

        return value