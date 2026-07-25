#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>

hd44780_I2Cexp lcd;

// WiFi
const char* ssid = "WIFI BAQUE";
const char* password = "Davidba1970";

// Backend
const char* serverUrl = "http://192.168.40.11:8000";

// Servo
#define SERVO_PIN 13
Servo doorServo;

// RGB LED integrado ESP32-S3
#include <Adafruit_NeoPixel.h>
#define RGB_PIN 48
#define NUM_LEDS 1
Adafruit_NeoPixel rgb(NUM_LEDS, RGB_PIN, NEO_GRB + NEO_KHZ800);

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  rgb.setPixelColor(0, rgb.Color(r, g, b));
  rgb.show();
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
    lcd.print("WiFi Conectado");
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