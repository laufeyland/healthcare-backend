import tensorflow as tf
import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image
import os


def ai_infer(model_path, path_to_image):
    """
    Load a Keras model and run inference on the given image.

    Args:
        Model_ID (str): Path to the Keras model (.h5 or .keras file).
        Path_to_image (str): Path to the medical scan image.

    Returns:
        tuple: (Predicted class label, Confidence score as a percentage)
    """
    # Load the model
    if not os.path.exists(model_path):
        raise ValueError(f"Model file does not exist: {model_path}")

    # Ensure correct model loading
    try:
        model = load_model(model_path)
    except Exception as e:
        raise ValueError(f"Error loading model: {str(e)}")

    # Load and preprocess the image (resize to 299x299 without loss in quality)
    img = Image.open(path_to_image)
    img = img.resize((299, 299), Image.LANCZOS)  # LANCZOS maintains quality
    img_array = np.array(img)

    # Ensure the image has 3 channels (RGB)
    if img_array.shape[-1] != 3:
        img_array = np.stack((img_array,) * 3, axis=-1) if len(img_array.shape) == 2 else img_array[:, :, :3]

    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

    # Run inference
    predictions = model.predict(img_array)
    
    # Get the predicted class and confidence
    predicted_index = np.argmax(predictions, axis=1)[0]
    confidence = predictions[0][predicted_index] * 100  # Convert to percentage

    # Define class labels based on your dataset
    class_labels = ["Normal", "Pneumonia", "Lung Opacity", "Viral Pneumonia"]
    
    predicted_label = class_labels[predicted_index] if predicted_index < len(class_labels) else "Unknown"

    return predicted_label, confidence

# Example usage:
# result, confidence = ai_infer("model.h5", "scan.jpg")
# print(f"Prediction: {result}, Confidence: {confidence:.2f}%")
