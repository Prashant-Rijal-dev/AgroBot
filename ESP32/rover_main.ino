/*
 * AgroBot Rover — ESP32 Firmware (no camera)
 *
 * What this does:
 *   1. Reads NPK / Temperature / Humidity / EC from RS485 Modbus sensor
 *   2. POSTs readings to the Flask server every SENSOR_INTERVAL ms
 *   3. Polls the server for the latest direction command every NAV_INTERVAL ms
 *      (The farmer uploads a field photo on the website; the CNN computes the
 *       direction; the rover picks it up here and drives accordingly.)
 *
 * Libraries (install via Arduino Library Manager):
 *   - ArduinoJson  by Benoit Blanchon
 *   - ModbusMaster by Doc Walker
 *
 * RS485 Wiring:
 *   DE/RE pin → GPIO 4
 *   Module TX → GPIO 17  (Serial2 RX on ESP32)
 *   Module RX → GPIO 16  (Serial2 TX on ESP32)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ModbusMaster.h>

// ─── Configuration ────────────────────────────────────────────────────────

const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://192.168.1.100:5001";  // your PC's local IP
const char* ROVER_KEY     = "agrobot-rover-key-2025";
const int   USER_ID       = 1;   // farmer account ID this rover belongs to

#define SENSOR_INTERVAL  10000   // ms between sensor readings
#define NAV_INTERVAL      3000   // ms between direction polls

// ─── RS485 pins ───────────────────────────────────────────────────────────

#define RS485_DE_RE 4

ModbusMaster node;
void preTransmission()  { digitalWrite(RS485_DE_RE, HIGH); }
void postTransmission() { digitalWrite(RS485_DE_RE, LOW);  }

// ─── Motor pins (adjust to your driver) ──────────────────────────────────

#define MOTOR_L_FWD 25
#define MOTOR_L_BWD 26
#define MOTOR_R_FWD 27
#define MOTOR_R_BWD 14

void motorsStop()     { digitalWrite(MOTOR_L_FWD,0); digitalWrite(MOTOR_L_BWD,0);
                        digitalWrite(MOTOR_R_FWD,0); digitalWrite(MOTOR_R_BWD,0); }
void motorsForward()  { digitalWrite(MOTOR_L_FWD,1); digitalWrite(MOTOR_L_BWD,0);
                        digitalWrite(MOTOR_R_FWD,1); digitalWrite(MOTOR_R_BWD,0); }
void motorsTurnLeft() { digitalWrite(MOTOR_L_FWD,0); digitalWrite(MOTOR_L_BWD,1);
                        digitalWrite(MOTOR_R_FWD,1); digitalWrite(MOTOR_R_BWD,0); }
void motorsTurnRight(){ digitalWrite(MOTOR_L_FWD,1); digitalWrite(MOTOR_L_BWD,0);
                        digitalWrite(MOTOR_R_FWD,0); digitalWrite(MOTOR_R_BWD,1); }

// ─── Sensor data struct ───────────────────────────────────────────────────

struct SensorData {
  float nitrogen    = 0;
  float phosphorus  = 0;
  float potassium   = 0;
  float temperature = 0;
  float humidity    = 0;
  float ec          = 0;
  bool  valid       = false;
};

unsigned long lastSensorMs = 0;
unsigned long lastNavMs    = 0;

// ─── Setup ────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);

  // RS485
  pinMode(RS485_DE_RE, OUTPUT);
  digitalWrite(RS485_DE_RE, LOW);
  Serial2.begin(9600, SERIAL_8N1, 17, 16);
  node.begin(1, Serial2);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  // Motors
  pinMode(MOTOR_L_FWD, OUTPUT); pinMode(MOTOR_L_BWD, OUTPUT);
  pinMode(MOTOR_R_FWD, OUTPUT); pinMode(MOTOR_R_BWD, OUTPUT);
  motorsStop();

  // WiFi
  Serial.printf("Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nConnected — IP: %s\n", WiFi.localIP().toString().c_str());
}

// ─── Read RS485 Sensor ────────────────────────────────────────────────────
/*
 * Register map for common 7-in-1 RS485 soil sensors (Modbus RTU, address 1):
 *   0x0000 — Humidity    (×0.1 %)
 *   0x0001 — Temperature (×0.1 °C, signed)
 *   0x0002 — EC          (µS/cm)
 *   0x0003 — pH          (×0.1)
 *   0x0004 — Nitrogen    (mg/kg)
 *   0x0005 — Phosphorus  (mg/kg)
 *   0x0006 — Potassium   (mg/kg)
 *
 * Adjust register addresses if your sensor uses a different layout.
 */
SensorData readSensor() {
  SensorData d;
  uint8_t result = node.readHoldingRegisters(0x0000, 7);
  if (result == node.ku8MBSuccess) {
    d.humidity    = node.getResponseBuffer(0) * 0.1f;
    d.temperature = (int16_t)node.getResponseBuffer(1) * 0.1f;
    d.ec          = node.getResponseBuffer(2);
    d.nitrogen    = node.getResponseBuffer(4);
    d.phosphorus  = node.getResponseBuffer(5);
    d.potassium   = node.getResponseBuffer(6);
    d.valid = true;
    Serial.printf("[Sensor] T=%.1f°C  Hum=%.1f%%  EC=%.0f  N=%.0f  P=%.0f  K=%.0f\n",
      d.temperature, d.humidity, d.ec, d.nitrogen, d.phosphorus, d.potassium);
  } else {
    Serial.printf("[Sensor] Modbus error 0x%02X\n", result);
  }
  return d;
}

// ─── POST sensor data ─────────────────────────────────────────────────────

void sendSensorData(const SensorData& d) {
  HTTPClient http;
  http.begin(String(SERVER_URL) + "/api/rover/data");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Rover-Key", ROVER_KEY);

  StaticJsonDocument<256> doc;
  doc["user_id"]     = USER_ID;
  doc["nitrogen"]    = d.nitrogen;
  doc["phosphorus"]  = d.phosphorus;
  doc["potassium"]   = d.potassium;
  doc["temperature"] = d.temperature;
  doc["humidity"]    = d.humidity;
  doc["ec"]          = d.ec;
  // If you add a GPS module later, include lat/lon here:
  // doc["latitude"]  = gps.location.lat();
  // doc["longitude"] = gps.location.lng();

  String body;
  serializeJson(doc, body);
  int code = http.POST(body);
  Serial.printf("[Data] POST → HTTP %d\n", code);
  http.end();
}

// ─── Poll direction command ───────────────────────────────────────────────
/*
 * The farmer uploads a field photo on the AgroBot website.
 * The CNN detects the path and stores a direction (LEFT/STRAIGHT/RIGHT/STOP).
 * The rover polls this endpoint and drives accordingly.
 */
void pollAndExecuteDirection() {
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/rover/command?user_id=" + USER_ID
               + "&key=" + ROVER_KEY;
  http.begin(url);
  int code = http.GET();

  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<128> doc;
    if (!deserializeJson(doc, body)) {
      String dir = doc["direction"].as<String>();
      Serial.printf("[Nav] Direction = %s\n", dir.c_str());
      executeDirection(dir);
    }
  } else {
    Serial.printf("[Nav] Command poll failed: HTTP %d\n", code);
  }
  http.end();
}

void executeDirection(const String& dir) {
  if (dir == "STRAIGHT") {
    motorsForward();
    delay(600);
    motorsStop();
  } else if (dir == "LEFT") {
    motorsTurnLeft();
    delay(350);
    motorsStop();
  } else if (dir == "RIGHT") {
    motorsTurnRight();
    delay(350);
    motorsStop();
  } else {
    motorsStop();  // STOP or UNKNOWN
  }
}

// ─── Main loop ────────────────────────────────────────────────────────────

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    WiFi.reconnect();
    delay(2000);
    return;
  }

  unsigned long now = millis();

  if (now - lastSensorMs >= SENSOR_INTERVAL) {
    lastSensorMs = now;
    SensorData d = readSensor();
    if (d.valid) sendSensorData(d);
  }

  if (now - lastNavMs >= NAV_INTERVAL) {
    lastNavMs = now;
    pollAndExecuteDirection();
  }
}
