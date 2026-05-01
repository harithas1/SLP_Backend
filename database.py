from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["lakshya_db"]

categories_collection = db["categories"]
products_collection = db["products"]
orders_collection = db["orders"]