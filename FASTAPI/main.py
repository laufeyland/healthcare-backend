import os
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from tensorflow.keras.models import load_model
from PIL import Image
import io
from pydantic import BaseModel
from typing import List

app = FastAPI()

CLASS_LABELS_MULTICLASS = ["Pneumonia", "Normal", "Lung Opacity"]
CLASS_LABELS_BINARY = ["Normal", "Pneumonia"]

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

        # Determine preprocessing strategy
        if "binary_classifier" in model_path.lower():
            # Preprocessing for binary classification model
            image = image.convert("RGB")
            image = image.resize((224, 224), Image.LANCZOS)
            img_array = np.array(image) / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            class_labels = CLASS_LABELS_BINARY

        elif "chest_xray_classification_final_model" in model_path.lower():
            # Preprocessing for multiclass model
            image = image.convert("L")
            image = image.resize((160, 160), Image.LANCZOS)
            img_array = np.array(image) / 255.0
            img_array = np.expand_dims(img_array, axis=-1)  # Add channel dimension
            img_array = np.expand_dims(img_array, axis=0)
            class_labels = CLASS_LABELS_MULTICLASS

        else:
            raise HTTPException(status_code=400, detail="Unknown model type for preprocessing.")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

    # Run prediction
    predictions = model.predict(img_array)

    # Handle binary or multiclass prediction logic
    if predictions.shape[1] == 1:
        # Binary classification (single sigmoid output)
        predicted_index = int(predictions[0][0] > 0.5)
        confidence = float(predictions[0][0] * 100) if predicted_index == 1 else float((1 - predictions[0][0]) * 100)
    else:
        # Multi-class classification (softmax output)
        predicted_index = int(np.argmax(predictions, axis=1)[0])
        confidence = float(predictions[0][predicted_index] * 100)

    predicted_label = class_labels[predicted_index] if predicted_index < len(class_labels) else "Unknown"

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