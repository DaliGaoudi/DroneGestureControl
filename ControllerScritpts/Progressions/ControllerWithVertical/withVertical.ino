#include <Arduino_BMI270_BMM150.h>
#include <ArduinoBLE.h>

float roll = 0, pitch = 0, yaw = 0;
const float sensitivity = 0.1;
const float threshold = 0.2;
float baseline_y = 0;

BLEService sensorService("180C");
BLECharacteristic sensorCharacteristic("2A56", BLERead | BLENotify | BLEWrite, 30);

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
  calibrateBaseline();
  Serial.println("Calibration complete!");

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
  float delta_y;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
    
    roll = atan2(y, z) * 180.0 / PI;
    pitch = atan2(-x, sqrt(y * y + z * z)) * 180.0 / PI;
    delta_y = y - baseline_y;
  }
  
  if (IMU.gyroscopeAvailable()) {
    IMU.readGyroscope(x, y, z);
    
    yaw += z * sensitivity;
    
    if (yaw > 180) yaw -= 360;
    if (yaw < -180) yaw += 360;
  }

  String data = String(roll) + " " + String(pitch) + " " + String(yaw) + " " + String(delta_y);
  sensorCharacteristic.writeValue(data.c_str());
  Serial.println(data);  // Debug print
}