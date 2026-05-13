




# app.py

import os
import csv
import time
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI

from dotenv import load_dotenv

load_dotenv()
# -----------------------------------
# Cloudinary Config
# -----------------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
    secure=True
)

app = FastAPI()

# Folder where you drop images
IMAGE_FOLDER = "./images"

# CSV file to save uploaded URLs
CSV_FILE = "uploaded_images.csv"

# Keep track of already uploaded files
uploaded_files = set()


def init_csv():
    """
    Create CSV file with headers if it doesn't exist
    """
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["file_name", "cloudinary_url", "public_id"])


def save_to_csv(file_name, url, public_id):
    """
    Save uploaded image info to CSV
    """
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([file_name, url, public_id])


def upload_new_images():
    """
    Scan folder continuously and upload new JPEG images
    """

    valid_extensions = (".jpg", ".jpeg")

    while True:
        try:
            files = os.listdir(IMAGE_FOLDER)

            for file_name in files:

                # Only process JPEG images
                if not file_name.lower().endswith(valid_extensions):
                    continue

                # Skip already uploaded files
                if file_name in uploaded_files:
                    continue

                file_path = os.path.join(IMAGE_FOLDER, file_name)

                print(f"Uploading: {file_name}")

                try:
                    result = cloudinary.uploader.upload(file_path)

                    image_url = result.get("secure_url")
                    public_id = result.get("public_id")

                    save_to_csv(file_name, image_url, public_id)

                    uploaded_files.add(file_name)

                    print(f"Uploaded: {file_name}")
                    print(f"URL: {image_url}")

                except Exception as e:
                    print(f"Error uploading {file_name}: {e}")

            # Check every 5 seconds
            time.sleep(5)

        except Exception as e:
            print("Folder scan error:", e)
            time.sleep(5)


@app.on_event("startup")
def startup_event():
    """
    Start background uploader on app startup
    """
    init_csv()

    import threading

    thread = threading.Thread(target=upload_new_images, daemon=True)
    thread.start()


@app.get("/")
def home():
    return {
        "message": "Automatic Cloudinary uploader is running"
    }