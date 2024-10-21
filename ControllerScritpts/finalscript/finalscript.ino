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
bool flying = false;
bool landingDetected = false;
bool landingConfirmed = false;
bool sendData = false;

const char* GESTURES[] = {
  "flip",
  "flex"
};

#define NUM_GESTURES (sizeof(GESTURES) / sizeof(GESTURES[0]))

BLEService sensorService("180C");
BLECharacteristic sensorCharacteristic("2A56", BLERead | BLENotify | BLEWrite, 30);

void setup() {
  pinMode(LEDR, OUTPUT);
  pinMode(LEDG, OUTPUT);
  pinMode(LEDB, OUTPUT);
  Serial.begin(9600);
  while (!Serial)
    ;

  if (!BLE.begin()) {
    Serial.println("Starting BLE failed!");
    while (1)
      ;
  }

  BLE.setLocalName("Nano33BLESense");
  BLE.setAdvertisedService(sensorService);
  sensorService.addCharacteristic(sensorCharacteristic);
  BLE.addService(sensorService);
  BLE.advertise();

  Serial.println("BLE device is now advertising");

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1)
      ;
  }
  Serial.println("IMU initialized.");
  calibrateBaseline();
  Serial.println("Calibration complete!");
  //red
  digitalWrite(LEDR, LOW);
  digitalWrite(LEDG, HIGH);
  digitalWrite(LEDB, HIGH);
  //
  if (!modelInit(model, tensorArena, tensorArenaSize)) {
    Serial.println("Model initialization failed!");
    //white
    digitalWrite(LEDR, LOW);
    digitalWrite(LEDG, LOW);
    digitalWrite(LEDB, LOW);
    while (true)
      ;
  }
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());
    // BLUE
    digitalWrite(LEDR, HIGH);
    digitalWrite(LEDG, HIGH);
    digitalWrite(LEDB, LOW);

    while (central.connected()) {
      Serial.println("Waiting for next command");
      if (!takeoffDetected) {
        Serial.println("1");
        if (true) {
          takeoffDetected = true;
          if(sensorCharacteristic.writeValue("flex")) {
            Serial.println("Take-off gesture detected! Waiting for confirmation...");
            delay(100);
          } else {
            Serial.println("Failed to send Signal 1");
          }
          // CYAN
          digitalWrite(LEDR, HIGH);
          digitalWrite(LEDG, LOW);
          digitalWrite(LEDB, LOW);
        } else {
          if(sensorCharacteristic.writeValue("wrong")) {
              Serial.println("Wrong Gesture sent");
              uint8_t buffer[30];
              int bytesRead = sensorCharacteristic.readValue(buffer, sizeof(buffer));
              String value(buffer, bytesRead);
              Serial.print("Received value: ");
              Serial.println(value);
              if (value == "wrong_confirmed") {
                Serial.println("received confirmation for wrong Gesture");
              }
              delay(500);
            } else {
              Serial.println("Failed to send signal 2");
            }
            
          digitalWrite(LEDR, LOW);
          digitalWrite(LEDG, LOW);
          digitalWrite(LEDB, HIGH);
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
            flying = true;
            sendData = true;
            // GREEN
            digitalWrite(LEDR, HIGH);
            digitalWrite(LEDG, LOW);
            digitalWrite(LEDB, HIGH);
          }
        }
      } else {
        delay(200);
        if (flying) {
          checkLanding();
          if (sendData) {
            updateAndSendData();
            }  
          }
      }
      delay(10);  // Small delay to prevent tight looping
    }

    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
    // RGB OFF
    digitalWrite(LEDR, HIGH);
    digitalWrite(LEDG, HIGH);
    digitalWrite(LEDB, HIGH);
    takeoffDetected = false;
    takeoffConfirmed = false;
  } 
}

bool recognizeFlip() {
  return false;
}

bool recognizeGesture() {
  float aX, aY, aZ, gX, gY, gZ;

  Serial.println("Detecting Gesture....");

  // wait for significant movement
  while (samplesRead == 0) {
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(aX, aY, aZ);
      float aSum = fabs(aX) + fabs(aY) + fabs(aZ);
      if (aSum >= accelerationThreshold) {
        break;
      } else {
        Serial.println("too much acceleration");
      }
    }
  }

  while (samplesRead < numSamples) {
    if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
      Serial.println("got acceleration and gyroscope data");
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
        if (!modelRunInference()) {
          Serial.println("RunInference Failed!");
          samplesRead = 0;
          return false;
        }

        if (modelGetOutput(1) * 100 > 60) {
          samplesRead = 0;
          Serial.println("Read flex");
          return true;
        } else {
          Serial.println("Wrong Gesture");
          return false;
        }

        samplesRead = 0;
        return false;
      }
    } else {
      Serial.println("Could not get accel or gyro");
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

void checkLanding() {
  float aX, aY, aZ;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(aX, aY, aZ);
    float totalAcceleration = sqrt(aX * aX + aY * aY + aZ * aZ);

    Serial.println(totalAcceleration);

    if (!landingDetected && (accelerationThreshold < totalAcceleration)) {
      if (recognizeGesture()) {
        landingDetected = true;
        sendData = false;
        sensorCharacteristic.writeValue("flex");
        Serial.println("Landing gesture detected! Waiting for confirmation...");
        // CYAN
        digitalWrite(LEDR, HIGH);
        digitalWrite(LEDG, HIGH);
        digitalWrite(LEDB, LOW);
      }

    } else if (!landingConfirmed) {
      // Wait for confirmation from Python script
      if (sensorCharacteristic.written()) {
        uint8_t buffer[30];
        int bytesRead = sensorCharacteristic.readValue(buffer, sizeof(buffer));
        String value(buffer, bytesRead);
        Serial.print("Received value: ");
        Serial.println(value);
        if (value == "landing_confirmed") {
          takeoffConfirmed = true;
          Serial.println("landing confirmed. Waiting for futher commands");
          flying = false;
          // GREEN
          digitalWrite(LEDR, HIGH);
          digitalWrite(LEDG, LOW);
          digitalWrite(LEDB, HIGH);
        }
      }
    }
  }
}

void updateAndSendData() {
  float aX, aY, aZ;

  float x, y, z;
  float delta_y;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);
    float totalAcceleration = sqrt(x * x + y * y + z * z);
    if (totalAcceleration < accelerationThreshold) {
      roll = atan2(y, z) * 180.0 / PI;
      pitch = atan2(x, sqrt(y * y + z * z)) * 180.0 / PI;
      delta_y = y - baseline_y;

      if (IMU.gyroscopeAvailable()) {
        IMU.readGyroscope(x, y, z);

        yaw += z * sensitivity;

        if (yaw > 180) yaw = 360;
        if (yaw < -180) yaw += 360;
      }

      String data = String(roll) + " " + String(pitch) + " " + String(yaw) + " " + String(delta_y);
      sensorCharacteristic.writeValue(data.c_str());
      Serial.println(data);  // Debug print
    }
  }
}