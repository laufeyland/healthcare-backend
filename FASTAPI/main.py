import os
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from tensorflow.keras.models import load_model
from PIL import Image
import io

app = FastAPI()

# Define class labels based on dataset
CLASS_LABELS = ["Normal", "Pneumonia", "Lung Opacity", "Viral Pneumonia"]

@app.post("/predict")
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
        image = image.convert("RGB")  # Ensure it's in RGB format
        image = image.resize((299, 299), Image.LANCZOS)  # Resize while maintaining quality
        img_array = np.array(image) / 255.0  # Normalize pixel values
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")

    predictions = model.predict(img_array)

   
    predicted_index = int(np.argmax(predictions, axis=1)[0])
    confidence = float(predictions[0][predicted_index] * 100)  

    predicted_label = CLASS_LABELS[predicted_index] if predicted_index < len(CLASS_LABELS) else "Unknown"

    return {"predicted_label": predicted_label, "confidence": confidence}
