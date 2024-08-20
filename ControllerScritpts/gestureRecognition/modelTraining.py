# Setup environment
# brew install vim
# pip install pandas numpy matplotlib
# pip install tensorflow==2.16.0-rc0
# pip install --upgrade pandas-gbq google-auth-oauthlib tensorflow tf-keras
# pip install scikit-learn


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
import seaborn as sns
import os
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report


print(f"TensorFlow version = {tf.__version__}\n")

# Set a fixed random seed value, for reproducibility
SEED = 1337
np.random.seed(SEED)
tf.random.set_seed(SEED)

GESTURES = [
    "flip",
    "newFlex",
]

SAMPLES_PER_GESTURE = 119
NUM_GESTURES = len(GESTURES)
ONE_HOT_ENCODED_GESTURES = np.eye(NUM_GESTURES)

inputs = []
outputs = []

# Read and process data
for gesture_index in range(NUM_GESTURES):
    gesture = GESTURES[gesture_index]
    print(f"Processing index {gesture_index} for gesture '{gesture}'.")

    output = ONE_HOT_ENCODED_GESTURES[gesture_index]

    df = pd.read_csv("/Users/amine/Documents/Backupdrone/" + gesture + ".csv")
    num_recordings = int(df.shape[0] / SAMPLES_PER_GESTURE)
    print(f"\tThere are {num_recordings} recordings of the {gesture} gesture.")

    columns_to_convert = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
    for col in columns_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    for i in range(num_recordings):
        tensor = []
        for j in range(SAMPLES_PER_GESTURE):
            index = i * SAMPLES_PER_GESTURE + j
            tensor += [
                (df['aX'][index] + 4) / 8,
                (df['aY'][index] + 4) / 8,
                (df['aZ'][index] + 4) / 8,
                (df['gX'][index] + 2000) / 4000,
                (df['gY'][index] + 2000) / 4000,
                (df['gZ'][index] + 2000) / 4000
            ]

        inputs.append(tensor)
        outputs.append(output)

inputs = np.array(inputs)
outputs = np.array(outputs)

# Check for NaN or infinite values in raw data
print("Check for NaN or infinite values in raw data:")
print(np.isnan(inputs).any(), np.isinf(inputs).any())
print(np.isnan(outputs).any(), np.isinf(outputs).any())

# Replace NaN and infinite values with zeros
inputs[np.isnan(inputs)] = 0
inputs[np.isinf(inputs)] = 0

print("Data set parsing and preparation complete.")

# Randomize the order of the inputs
num_inputs = len(inputs)
randomize = np.arange(num_inputs)
np.random.shuffle(randomize)
inputs = inputs[randomize]
outputs = outputs[randomize]

# Split the recordings into training, testing, and validation sets
TRAIN_SPLIT = int(0.6 * num_inputs)
TEST_SPLIT = int(0.2 * num_inputs + TRAIN_SPLIT)
inputs_train, inputs_test, inputs_validate = np.split(inputs, [TRAIN_SPLIT, TEST_SPLIT])
outputs_train, outputs_test, outputs_validate = np.split(outputs, [TRAIN_SPLIT, TEST_SPLIT])

print("Data set randomization and splitting complete.")


# Normalize the data
scaler = StandardScaler()
inputs_train_scaled = scaler.fit_transform(inputs_train)
inputs_validate_scaled = scaler.transform(inputs_validate)
inputs_test_scaled = scaler.transform(inputs_test)

# Check if the scaling process worked correctly
print("Range of scaled inputs:")
print("Train:", np.min(inputs_train_scaled), np.max(inputs_train_scaled))
print("Validate:", np.min(inputs_validate_scaled), np.max(inputs_validate_scaled))
print("Test:", np.min(inputs_test_scaled), np.max(inputs_test_scaled))

# Build and train the model
model = tf.keras.Sequential()
model.add(tf.keras.layers.Dense(50, activation='relu', input_shape=(inputs_train_scaled.shape[1],)))
model.add(tf.keras.layers.Dense(15, activation='relu'))
model.add(tf.keras.layers.Dense(NUM_GESTURES, activation='softmax'))
model.compile(optimizer='rmsprop', loss='mse', metrics=['mae'])

history = model.fit(inputs_train, outputs_train, epochs=2000, batch_size=1, validation_data=(inputs_validate, outputs_validate))

# increase the size of the graphs. The default size is (6,4).

plt.rcParams["figure.figsize"] = (20,10)

# Compute predictions
predictions = model.predict(inputs_test)
y_true = np.argmax(outputs_test, axis=1)
y_pred = np.argmax(predictions, axis=1)

# Calculate precision, recall, and F1 score
precision = precision_score(y_true, y_pred, average=None)
recall = recall_score(y_true, y_pred, average=None)
f1 = f1_score(y_true, y_pred, average=None)

# Print precision, recall, and F1 score for each class
for i, gesture in enumerate(GESTURES):
    print(f"{gesture}:")
    print(f"  Precision: {precision[i]:.2f}")
    print(f"  Recall: {recall[i]:.2f}")
    print(f"  F1 Score: {f1[i]:.2f}")

# Alternatively, print a classification report which includes precision, recall, and F1 score
report = classification_report(y_true, y_pred, target_names=GESTURES)
print("\nClassification Report:\n", report)

# graph the loss, the model above is configure to use "mean squared error" as the loss function
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs = range(1, len(loss) + 1)
plt.plot(epochs, loss, 'g.', label='Training loss')
plt.plot(epochs, val_loss, 'b', label='Validation loss')
plt.title('Training and validation loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.show()

print(plt.rcParams["figure.figsize"])

# graph the loss again skipping a bit of the start
SKIP = 100
plt.plot(epochs[SKIP:], loss[SKIP:], 'g.', label='Training loss')
plt.plot(epochs[SKIP:], val_loss[SKIP:], 'b.', label='Validation loss')
plt.title('Training and validation loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.show()

# graph of mean absolute error
mae = history.history['mae']
val_mae = history.history['val_mae']
plt.plot(epochs[SKIP:], mae[SKIP:], 'g.', label='Training MAE')
plt.plot(epochs[SKIP:], val_mae[SKIP:], 'b.', label='Validation MAE')
plt.title('Training and validation mean absolute error')
plt.xlabel('Epochs')
plt.ylabel('MAE')
plt.legend()
plt.show()

# Compute confusion matrix
predictions = model.predict(inputs_test)
y_true = np.argmax(outputs_test, axis=1)
y_pred = np.argmax(predictions, axis=1)
conf_matrix = confusion_matrix(y_true, y_pred)

# Plot confusion matrix
plt.figure(figsize=(10, 7))
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', 
            xticklabels=GESTURES, yticklabels=GESTURES)
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

# # Convert the model to the TensorFlow Lite format without quantization
# converter = tf.lite.TFLiteConverter.from_keras_model(model)
# tflite_model = converter.convert()

# # Save the model to disk
# open("gesture_model.tflite", "wb").write(tflite_model)


# basic_model_size = os.path.getsize("gesture_model.tflite")
# print("Model is %d bytes" % basic_model_size)

#check out the collablink to get converted header files: 
#https://colab.research.google.com/drive/1Jj_LjUFtrzhLT6QaVmfLupGtPSITQi5Q#scrollTo=9J33uwpNtAku