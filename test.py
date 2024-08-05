import tensorflow as tf
import os

# Define a simple model for testing
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(4,)),  # Correctly defined input layer
    tf.keras.layers.Dense(10, activation='relu'),
    tf.keras.layers.Dense(3, activation='softmax')
])

# Compile the model
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

# Convert the model to TensorFlow Lite format
try:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    
    # Save the model to disk
    model_file = "gesture_model.tflite"
    with open(model_file, "wb") as f:
        f.write(tflite_model)
    
    # Print the size of the converted model
    model_size = os.path.getsize(model_file)
    print(f"Model successfully converted and saved as '{model_file}' with size {model_size} bytes.")
except Exception as e:
    print(f"Error during model conversion: {e}")
