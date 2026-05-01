from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import categories_collection, products_collection
from bson import ObjectId
import cloudinary.uploader

router = APIRouter()


# ✅ CREATE CATEGORY (WITH IMAGE UPLOAD)
@router.post("/categories")
async def create_category(
    name: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        print("Received:", name, image.filename)  # 🔥 DEBUG

        upload_result = cloudinary.uploader.upload(await image.read())

        print("Cloudinary:", upload_result)  # 🔥 DEBUG

        image_url = upload_result.get("secure_url")

        if not image_url:
            raise HTTPException(status_code=400, detail="Image upload failed")

        category = {
            "name": name,
            "image": image_url
        }

        result = categories_collection.insert_one(category)

        return {
            "id": str(result.inserted_id),
            "image": image_url
        }

    except Exception as e:
        print("ERROR:", str(e))  # 🔥 VERY IMPORTANT
        raise HTTPException(status_code=500, detail=str(e))

    
# ✅ GET
@router.get("/categories")
def get_categories():
    data = []
    for c in categories_collection.find():
        c["_id"] = str(c["_id"])
        data.append(c)
    return data


# ✅ DELETE
@router.delete("/categories/{id}")
def delete_category(id: str):
    category = categories_collection.find_one({"_id": ObjectId(id)})

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    products_collection.delete_many({"category": category["name"]})
    categories_collection.delete_one({"_id": ObjectId(id)})

    return {"message": "Category deleted"}