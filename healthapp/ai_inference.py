## FILE NOT USED ANYMORE, SEE FASTAPI INTEGRATION

import tensorflow as tf
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image
import os


def ai_infer(model_path, path_to_image):
    if not os.path.exists(model_path):
        raise ValueError(f"Model file does not exist: {model_path}")


    try:
        model = load_model(model_path)
    except Exception as e:
        raise ValueError(f"Error loading model: {str(e)}")


    img = Image.open(path_to_image)
    img = img.resize((299, 299), Image.LANCZOS)  
    img_array = np.array(img)

    if img_array.shape[-1] != 3:
        img_array = np.stack((img_array,) * 3, axis=-1) if len(img_array.shape) == 2 else img_array[:, :, :3]

    img_array = np.expand_dims(img_array, axis=0)  

    predictions = model.predict(img_array)
    
    predicted_index = np.argmax(predictions, axis=1)[0]
    confidence = predictions[0][predicted_index] * 100  

    class_labels = ["Normal", "Pneumonia", "Lung Opacity", "Viral Pneumonia"]
    
    predicted_label = class_labels[predicted_index] if predicted_index < len(class_labels) else "Unknown"

    return predicted_label, confidence