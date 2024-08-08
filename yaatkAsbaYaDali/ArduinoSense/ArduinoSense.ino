#include <Arduino_LSM9DS1.h>
#include <ArduinoBLE.h>

void setup() {
  Serial.begin(9600);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  BLE.begin();
  BLE.setLocalName("GestureSensor");
  BLE.advertise();
  
  Serial.println("BLE and IMU initialized.");
}

void loop() {
  // Variables to hold sensor readings
  float x, y, z;

  // Check if new accelerometer data is available
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);

    // Simple gesture recognition example
    String gesture = recognizeGesture(x, y, z);
    
    // Send gesture over BLE
    BLE.poll();
    BLEDevice central = BLE.central();
    
    if (central) {
      central.write(gesture.c_str());
    }
  }

  delay(100);
}

String recognizeGesture(float x, float y, float z) {
  if (x > 1.0) {
    return "RIGHT";
  } else if (x < -1.0) {
    return "LEFT";
  } else if (y > 1.0) {
    return "UP";
  } else if (y < -1.0) {
    return "DOWN";
  } else {
    return "NONE";
  }
}