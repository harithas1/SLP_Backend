import os
from pymongo import MongoClient



MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client["lakshya_db"]

categories_collection = db["categories"]
products_collection = db["products"]
orders_collection = db["orders"]