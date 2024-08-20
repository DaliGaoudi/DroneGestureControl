import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_data(df, columns, title, y_label):
    plt.figure(figsize=(20, 10))
    for col, color in zip(columns, ['g', 'b', 'r']):
        plt.plot(df.index, df[col], color=color, label=col[-1], linestyle='solid', marker=',')
    plt.title(title)
    plt.xlabel("Sample #")
    plt.ylabel(y_label)
    plt.legend()
    plt.show()

def validate_and_convert_data(df):
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except ValueError as e:
            print(f"Error converting column {col}: {e}")
            print(f"Sample values from {col}:", df[col].head())
    return df

# Read the CSV file
filename = "flex.csv"
file_path = "/Users/amine/Documents/Backupdrone/" + filename
df = pd.read_csv(file_path)

print("Original DataFrame info:")
print(df.info())
print("\nFirst few rows of the original DataFrame:")
print(df.head())

# Check if the required columns exist
required_columns = ['aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
if not all(col in df.columns for col in required_columns):
    raise ValueError(f"CSV file is missing one or more required columns: {required_columns}")

# Validate and convert data
df = validate_and_convert_data(df)

print("\nDataFrame info after conversion:")
print(df.info())
print("\nFirst few rows after conversion:")
print(df.head())

# Set the index to start from 1
df.index = range(1, len(df) + 1)

# Plot acceleration data
plot_data(df, ['aX', 'aY', 'aZ'], "Acceleration", "Acceleration (G)")

# Plot gyroscope data
plot_data(df, ['gX', 'gY', 'gZ'], "Gyroscope", "Gyroscope (deg/sec)")

print("Plotting complete. Check the displayed figures.")