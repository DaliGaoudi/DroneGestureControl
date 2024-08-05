#include <Arduino_BMI270_BMM150.h>
#include <ArduinoBLE.h>

float roll = 0, pitch = 0, yaw = 0;
const float sensitivity = 0.1;
const float threshold = 0.2;
float baseline_y = 0;

BLEService sensorService("180C");
BLECharacteristic sensorCharacteristic("2A56", BLERead | BLENotify, 30);

float lastVertical = 0;
float verticalOffset = 0;
bool isCalibrated = false;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  Serial.println("IMU initialized. Place the device flat and still for calibration.");
  delay(2000); // Wait for the device to be placed still
  calibrateBaseline();
  Serial.println("Calibration complete. Ready to go!");
}

void loop() {
      updateAndSendData();
  
  delay(50); // Adjust delay as needed
}

void calibrateBaseline() {
  float sum_y = 0;
  int samples = 100;
  
  for (int i = 0; i < samples; i++) {
    float x, y, z;
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(x, y, z);
      sum_y += y;
    }
    delay(10);
  }
  
  baseline_y = sum_y / samples;
  Serial.print("Baseline Y: ");
  Serial.println(baseline_y);
}


void updateAndSendData() {
  float x, y, z;
  float vertical = 0;
  float delta_y;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
    
    roll = atan2(y, z) * 180.0 / PI;
    pitch = atan2(-x, sqrt(y * y + z * z)) * 180.0 / PI;
    delta_y = y - baseline_y;

    if (delta_y > threshold) {
      Serial.println("Moving up");
    } else if (delta_y < -threshold) {
      Serial.println("Moving down");
    }

  }
  
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(x, y, z);
    
    // Calculate yaw (simple integration)
    yaw += z * sensitivity;
    
    // Keep yaw between -180 and 180 degrees
    if (yaw > 180) yaw -= 360;
    if (yaw < -180) yaw += 360;
  }

  // Output roll, pitch, yaw, and vertical values
  String data = String(roll) + " " + String(pitch) + " " + String(yaw) + " " + String(delta_y);
  Serial.println(data);
  sensorCharacteristic.writeValue(data.c_str());
}