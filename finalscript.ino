#include <Arduino_BMI270_BMM150.h>
#include <ArduinoBLE.h>
#include <ArduTFLite.h>
#include "model.h"

float roll = 0, pitch = 0, yaw = 0;
const float sensitivity = 0.1;
const float threshold = 0.2;
float baseline_y = 0;

const float accelerationThreshold = 2.5; 
const int numSamples = 119; 

int samplesRead = 0;
const int inputLength = 714; 

constexpr int tensorArenaSize = 8 * 1024;
alignas(16) byte tensorArena[tensorArenaSize];

bool takeoffDetected = false;
bool takeoffConfirmed = false;

const char* GESTURES[] = {
  "flip",
  "flex"
};

#define NUM_GESTURES (sizeof(GESTURES) / sizeof(GESTURES[0]))

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

  if (!modelInit(model, tensorArena, tensorArenaSize)){
    Serial.println("Model initialization failed!");
    while(true);
  }
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());
    
    while (central.connected()) {
      if (!takeoffDetected) {
        if (recognizeGesture()) {
          takeoffDetected = true;
          sensorCharacteristic.writeValue("flex");
          Serial.println("Take-off gesture detected! Waiting for confirmation...");
        }
      } else if (!takeoffConfirmed) {
        // Wait for confirmation from Python script
        if (sensorCharacteristic.written()) {
          uint8_t buffer[30];
          int bytesRead = sensorCharacteristic.readValue(buffer, sizeof(buffer));
          String value(buffer, bytesRead);
          Serial.print("Received value: ");
          Serial.println(value);
          if (value == "takeoff_confirmed") {
            takeoffConfirmed = true;
            Serial.println("Takeoff confirmed. Starting continuous data stream.");
          }
        }
      } else {
        delay(20);
        updateAndSendData();
      }
      delay(10);  // Small delay to prevent tight looping
    }

    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
    takeoffDetected = false;
    takeoffConfirmed = false;
    BLE.advertise();  // Start advertising again
  }
}

bool recognizeFlip() {
  return false;
}

bool recognizeGesture() {
  float aX, aY, aZ, gX, gY, gZ;

  // wait for significant movement
  while (samplesRead == 0) {
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(aX, aY, aZ);
      float aSum = fabs(aX) + fabs(aY) + fabs(aZ);
      if (aSum >= accelerationThreshold) {
        break;
      }
    }
  }

  while (samplesRead < numSamples) {
    if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
      IMU.readAcceleration(aX, aY, aZ);
      IMU.readGyroscope(gX, gY, gZ);

      aX = (aX + 4.0) / 8.0;
      aY = (aY + 4.0) / 8.0;
      aZ = (aZ + 4.0) / 8.0;
      gX = (gX + 2000.0) / 4000.0;
      gY = (gY + 2000.0) / 4000.0;
      gZ = (gZ + 2000.0) / 4000.0;
      
      modelSetInput(aX, samplesRead * 6 + 0);
      modelSetInput(aY, samplesRead * 6 + 1);
      modelSetInput(aZ, samplesRead * 6 + 2); 
      modelSetInput(gX, samplesRead * 6 + 3);
      modelSetInput(gY, samplesRead * 6 + 4);
      modelSetInput(gZ, samplesRead * 6 + 5); 
      
      samplesRead++;
      
      if (samplesRead == numSamples) {
        if(!modelRunInference()){
          Serial.println("RunInference Failed!");
          samplesRead = 0;
          return false;
        }

        if (modelGetOutput(1) * 100 > 90) {
          samplesRead = 0;
          return true;
        }

        samplesRead = 0;
        return false;
      }
    }
  }
  
  return false;
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