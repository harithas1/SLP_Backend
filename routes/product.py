from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from database import products_collection
from bson import ObjectId
import cloudinary.uploader

router = APIRouter()


# ✅ CREATE PRODUCT (UPLOAD IMAGE + SAVE)
@router.post("/products")
async def create_product(
    title: str = Form(...),
    price: int = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # 🔥 Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(await image.read())

        image_url = upload_result.get("secure_url")

        if not image_url:
            raise HTTPException(status_code=400, detail="Image upload failed")

        # 🔥 Save to DB
        product = {
            "title": title,
            "price": price,
            "category": category,
            "image": image_url
        }

        result = products_collection.insert_one(product)

        return {
            "message": "Product added successfully",
            "id": str(result.inserted_id),
            "image": image_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ GET ALL PRODUCTS (FILTER SUPPORT)

@router.get("/products")
def get_products(
    category: Optional[str] = Query(None),
    max_price: Optional[int] = Query(None)
):
    try:
        query = {}

        # ✅ FIX: case-insensitive match
        if category:
            query["category"] = {"$regex": f"^{category}$", "$options": "i"}

        if max_price:
            query["price"] = {"$lte": max_price}

        products = []
        for p in products_collection.find(query):
            p["_id"] = str(p["_id"])
            products.append(p)

        return products

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ GET SINGLE PRODUCT
@router.get("/products/{id}")
def get_product(id: str):
    try:
        product = products_collection.find_one({"_id": ObjectId(id)})

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product["_id"] = str(product["_id"])
        return product

    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid ID")


# ✅ DELETE PRODUCT
@router.delete("/products/{id}")
def delete_product(id: str):
    try:
        result = products_collection.delete_one({"_id": ObjectId(id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")

        return {"message": "Product deleted successfully"}

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")