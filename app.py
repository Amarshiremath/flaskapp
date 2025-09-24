from flask import Flask, request, render_template
import pandas as pd
from pymongo import MongoClient
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

app = Flask(__name__)

# -----------------------------
# MongoDB Atlas setup
# -----------------------------
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable not set!")

client = MongoClient(MONGO_URI)
db = client['education_db']            # Database name
collection = db['topics']              # Main data collection
files_collection = db['uploaded_files'] # To track uploaded files

# -----------------------------
# Flask routes
# -----------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload-data', methods=['POST'])
def upload_data():
    file = request.files.get('file')
    if not file:
        return render_template('index.html', message="❌ No file selected.")

    file_content = file.read()
    file_hash = hashlib.md5(file_content).hexdigest()

    # Check if this file was already uploaded
    if files_collection.find_one({"file_hash": file_hash}):
        return render_template('index.html', message="⚠️ This file has already been uploaded.")

    # Reset file pointer to read data again
    file.seek(0)
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return render_template('index.html', message="❌ Error reading the Excel file.")

    data = df.to_dict(orient='records')

    # Transform flat data → nested schema
    transformed_data = []
    for row in data:
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

    if transformed_data:
        collection.insert_many(transformed_data)
        files_collection.insert_one({"file_hash": file_hash})
        return render_template('index.html', message="✅ Data uploaded successfully!")

    return render_template('index.html', message="❌ The file is empty or invalid.")

# -----------------------------
# Run the app (local)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
