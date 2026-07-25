#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Servo.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "TU_WIFI_SSID";
const char* password = "TU_WIFI_PASSWORD";

// Backend URL
const char* serverUrl = "http://192.168.1.100:8000";

// RFID pins
#define SS_PIN 5
#define RST_PIN 22
MFRC522 rfid(SS_PIN, RST_PIN);

// Servo pin
#define SERVO_PIN 13
Servo doorServo;

// LED pins
#define LED_GREEN 27
#define LED_RED 26
#define BUZZER 14

String lastCardId = "";
unsigned long lastCardTime = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  
  doorServo.attach(SERVO_PIN);
  doorServo.write(0);
  
  SPI.begin();
  rfid.PCD_Init();
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  String cardId = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    cardId += String(rfid.uid.uidByte[i], HEX);
  }
  cardId.toUpperCase();

  Serial.println("Card detected: " + cardId);

  if (sendAccessRequest(cardId)) {
    grantAccess();
  } else {
    denyAccess();
  }

  delay(1000);
}

bool sendAccessRequest(String cardId) {
  HTTPClient http;
  http.begin(String(serverUrl) + "/api/logs");
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc;
  doc["person"] = cardId;
  doc["type"] = "entry";
  doc["method"] = "rfid";
  doc["helmet"] = true;
  doc["status"] = "authorized";
  doc["timestamp"] = "";

  String requestBody;
  serializeJson(doc, requestBody);

  int httpCode = http.POST(requestBody);
  http.end();

  return httpCode == 200;
}

void grantAccess() {
  Serial.println("Access GRANTED");
  digitalWrite(LED_GREEN, HIGH);
  tone(BUZZER, 1000, 200);
  doorServo.write(90);
  delay(3000);
  doorServo.write(0);
  digitalWrite(LED_GREEN, LOW);
}

void denyAccess() {
  Serial.println("Access DENIED");
  digitalWrite(LED_RED, HIGH);
  tone(BUZZER, 200, 500);
  delay(2000);
  digitalWrite(LED_RED, LOW);
}