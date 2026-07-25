#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>
#include <Adafruit_NeoPixel.h>

hd44780_I2Cexp lcd;

// WiFi
const char* ssid = "WIFI BAQUE";
const char* password = "Davidba1970";

// Firebase
const char* projectId = "iot-security-dashboard-f4c31";
const char* apiKey = "AIzaSyBaCk0gP31rLu1nN-p1h_g9eDvl8H1EeKA";

// Servo
#define SERVO_PIN 13
Servo doorServo;

// RGB LED
#define RGB_PIN 48
#define NUM_LEDS 1
Adafruit_NeoPixel rgb(NUM_LEDS, RGB_PIN, NEO_GRB + NEO_KHZ800);

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  rgb.setPixelColor(0, rgb.Color(r, g, b));
  rgb.show();
}

bool sendToFirestore(String collection, String jsonBody) {
  HTTPClient http;
  String url = "https://firestore.googleapis.com/v1/projects/";
  url += projectId;
  url += "/databases/(default)/documents/";
  url += collection;
  url += "?key=";
  url += apiKey;

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  int httpCode = http.POST(jsonBody);
  http.end();
  return httpCode == 200;
}

void setup() {
  Serial.begin(115200);

  rgb.begin();
  rgb.setBrightness(50);
  setRGB(0, 0, 255);

  doorServo.attach(SERVO_PIN);
  doorServo.write(0);

  Wire.begin(21, 18);
  lcd.begin(16, 2);
  lcd.backlight();
  lcd.print("Iniciando...");

  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  lcd.clear();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK");
    setRGB(0, 255, 0);
    lcd.setCursor(0, 0);
    lcd.print("IoT Security");
    lcd.setCursor(0, 1);
    lcd.print("Firebase listo");
  } else {
    setRGB(255, 0, 0);
    lcd.setCursor(0, 0);
    lcd.print("WiFi ERROR");
  }

  delay(1500);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Sistema listo");
  lcd.setCursor(0, 1);
  lcd.print("1=Abrir 2=Cerrar");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '1') {
      abrirPuerta();
    } else if (cmd == '2') {
      cerrarPuerta();
    }
  }
}

void abrirPuerta() {
  Serial.println("Abriendo puerta...");
  setRGB(0, 255, 0);
  doorServo.write(90);

  String json = "{\"fields\":{\"state\":{\"stringValue\":\"open\"},\"updatedAt\":{\"timestampValue\":\"2024-01-01T00:00:00Z\"}}}";
  sendToFirestore("controls/door", json);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Puerta ABIERTA");
  lcd.setCursor(0, 1);
  lcd.print("Bienvenido!");
}

void cerrarPuerta() {
  Serial.println("Cerrando puerta...");
  setRGB(255, 0, 0);
  doorServo.write(0);

  String json = "{\"fields\":{\"state\":{\"stringValue\":\"closed\"},\"updatedAt\":{\"timestampValue\":\"2024-01-01T00:00:00Z\"}}}";
  sendToFirestore("controls/door", json);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Puerta CERRADA");
  delay(1000);
  setRGB(0, 0, 255);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Sistema listo");
  lcd.setCursor(0, 1);
  lcd.print("1=Abrir 2=Cerrar");
}