#include <Arduino_BMI270_BMM150.h>
#include <ArduinoBLE.h>

float roll = 0, pitch = 0, yaw = 0;
const float sensitivity = 0.1;
const float verticalThreshold = 0.5; // Adjust this value to change sensitivity

BLEService sensorService("180C");
BLECharacteristic sensorCharacteristic("2A56", BLERead | BLENotify, 30);

void setup() {
 Serial.begin(9600);
  while (!Serial);

  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1);
  }

  BLE.setLocalName("Nano33BLESense");
  BLE.setAdvertisedService(sensorService);
  sensorService.addCharacteristic(sensorCharacteristic);
  BLE.addService(sensorService);
  BLE.advertise();

  Serial.println("BLE device is now advertising");

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  Serial.println("IMU initialized.");
}

void loop() {
  float x, y, z;

  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    while (central.connected()) {
      updateAndSendData();
    }
    
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
  
  
  delay(50); // Adjust delay as needed
}

void updateAndSendData() {

    float x,y,z;
    float vertical;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
    
    // Calculate roll and pitch
    roll = atan2(y, z) * 180.0 / PI;
    pitch = atan2(-x, sqrt(y * y + z * z)) * 180.0 / PI;


    vertical = z - 1.0; // Subtract 1g to account for gravity
    if (abs(vertical) < verticalThreshold) {
     if (vertical > 0) {
      vertical = 1; // Upward movement
    } else {
      vertical = -1; // Downward movement
    }
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

  // Output roll, pitch, and yaw values
 String data = String(roll) + " " + String(pitch) + " " + String(yaw) + " ";
 Serial.println(data);
 sensorCharacteristic.writeValue(data.c_str());
}
