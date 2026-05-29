# database.py

import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is not configured. Please check your .env file.")

client = MongoClient(MONGO_URL)
db = client["lakshya_db"]

categories_collection = db["categories"]
products_collection = db["products"]
orders_collection = db["orders"]

print("Connected DB:", db.name)
print("Products count:", products_collection.count_documents({}))


def ensure_indexes():
    try:
        products_collection.create_index(
            [("id", ASCENDING)],
            unique=True,
            partialFilterExpression={"id": {"$exists": True}},
        )

        products_collection.create_index(
            [("slug", ASCENDING)],
            unique=True,
            partialFilterExpression={"slug": {"$exists": True}},
        )

    except DuplicateKeyError as e:
        print("Duplicate product data found. Please clean products collection.")
        print(e)


ensure_indexes()