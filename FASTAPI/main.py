import os
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from tensorflow.keras.models import load_model
from PIL import Image
import io
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Define class labels based on dataset
CLASS_LABELS = ["Pneumonia", "Normal", "Lung Opacity"]

@app.post("/infer")
async def ai_infer(model_path: str = Query(..., description="Path to the trained Keras model"),
                   file: UploadFile = File(...)):
    """
    Load a Keras model and run inference on the given image.

    Args:
        model_path (str): Path to the Keras model (.h5 or .keras file).
        file (UploadFile): Medical scan image file.

    Returns:
        dict: {"predicted_label": str, "confidence": float}
    """

    if not os.path.exists(model_path):
        raise HTTPException(status_code=400, detail=f"Model file not found: {model_path}")

    try:
        model = load_model(model_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model: {str(e)}")

    try:
        image = Image.open(io.BytesIO(await file.read()))
        image = image.convert("L")  # "L" = grayscale (1 channel)
        image = image.resize((160, 160), Image.LANCZOS)  # Resize while maintaining quality
        img_array = np.array(image) / 255.0  # Normalize pixel values
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

    predictions = model.predict(img_array)

   
    predicted_index = int(np.argmax(predictions, axis=1)[0])
    confidence = float(predictions[0][predicted_index] * 100)  

    predicted_label = CLASS_LABELS[predicted_index] if predicted_index < len(CLASS_LABELS) else "Unknown"

    return {"predicted_label": predicted_label, "confidence": confidence}


class Doctor(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    wilaya: str
    license_number: str
    phone_number: str
    address: str
    status: str
    email: str
    external_id: str

@app.get("/approved-doctors", response_model=List[Doctor])
def get_approved_doctors():
    # fake data
    return [
        {
            "first_name": "Ali",
            "last_name": "Benali",
            "specialty": "Cardiology",
            "wilaya": "25",
            "license_number": "DOC-001",
            "phone_number": "0555123456",
            "status": "active",
            "address": "123 Rue Example",
            "email": "ali.benali@example.com",
            "external_id": "fastapi-001"
        },
        {
            "first_name": "Nora",
            "last_name": "Mekki",
            "specialty": "Dermatology",
            "wilaya": "16",
            "license_number": "DOC-002",
            "phone_number": "0555789456",
            "status": "inactive",
            "address": "456 Boulevard Central",
            "email": "nora.mekki@example.com",
            "external_id": "fastapi-002"
        },
        {
            "first_name": "Abdeldjalil",
            "last_name": "Bouchama",
            "specialty": "Neurology",
            "wilaya": "25",
            "license_number": "DOC-003",
            "phone_number": "0555789456",
            "status": "inactive",
            "address": "456 Boulevard Central",
            "email": "nora.mekki@example.com",
            "external_id": "fastapi-003"
        },
        {
            "first_name": "Abdeldjalil2",
            "last_name": "Bouchama2",
            "specialty": "Neurology",
            "wilaya": "25",
            "license_number": "DOC-004",
            "phone_number": "0555789456",
            "status": "inactive",
            "address": "456 Boulevard Central",
            "email": "nora.mekki@example.com",
            "external_id": "fastapi-004"
        }
        
    ]