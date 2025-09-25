from flask import Flask, request, render_template
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)

# -----------------------------
# MongoDB Atlas setup
# -----------------------------
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client['education_db']  # Main database


# -----------------------------
# Helpers
# -----------------------------
def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name to be MongoDB safe."""
    # Lowercase, strip spaces
    name = name.strip().lower()
    # Replace any non-alphanumeric with underscores
    name = re.sub(r'[^a-z0-9]+', '_', name)
    # Avoid leading/trailing underscores
    name = name.strip('_')
    return name or "default_collection"


# -----------------------------
# Flask routes
# -----------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload-data', methods=['POST'])
def upload_data():
    file = request.files.get('file')
    collection_name = request.form.get("collection_name")

    if not file:
        return render_template('index.html', message="❌ No file selected.")
    if not collection_name:
        return render_template('index.html', message="❌ Please enter a collection name.")

    # Sanitize collection name
    collection_name = sanitize_collection_name(collection_name)

    # Prevent overwriting if the same collection name already exists
    if collection_name in db.list_collection_names():
        return render_template('index.html',
                               message=f"⚠️ Collection '{collection_name}' already exists. Try another name.")

    # Read Excel file
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return render_template('index.html', message=f"❌ Error reading Excel file: {str(e)}")

    if df.empty:
        return render_template('index.html', message="❌ The file is empty or invalid.")

    # Transform flat data → nested schema
    transformed_data = []
    for row in df.to_dict(orient='records'):
        doc = {
            "title": row.get("Topic"),
            "subject": row.get("Subject"),
            "gradeLevel": row.get("Class"),
            "chapterNumber": row.get("Chapter", 1),
            "curriculum": row.get("Curriculum_Type", "General"),
            "description": row.get("Description"),
            "topics": [
                {
                    "title": row.get("Topic"),
                    "activities": [
                        {
                            "title": f"{row.get('Topic')} Activity",
                            "description": row.get("Description"),
                            "videos": {
                                "vrLink": row.get("VR_URL"),
                                "mobileLink": row.get("Video_URL"),
                                "demoLink": row.get("WebGL_URL")
                            },
                            "duration": 20
                        }
                    ]
                }
            ]
        }
        transformed_data.append(doc)

    # Insert into new collection
    collection = db[collection_name]
    collection.insert_many(transformed_data)

    return render_template('index.html', message=f"✅ File uploaded successfully into '{collection_name}' collection!")


# -----------------------------
# Run the app (local)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
