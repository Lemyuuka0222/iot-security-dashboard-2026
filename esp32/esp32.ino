#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>
#include <Adafruit_NeoPixel.h>
#include <SPI.h>
#include <MFRC522.h>

hd44780_I2Cexp lcd;

// ===== WiFi (misma red que la PC) =====
const char* ssid = "UTH Choluteca";
const char* password = "uth-2026";

// ===== PC con FastAPI (usar la IP que imprime el servidor) =====
const char* PC_URL = "http://10.11.8.27:8000";

// ===== RFID MFRC522 (SPI) =====
#define RFID_SCK  12
#define RFID_MOSI 11
#define RFID_MISO 10
#define RFID_SS   9
#define RFID_RST  5
MFRC522 rfid(RFID_SS, RFID_RST);

// ===== Servo =====
#define SERVO_PIN 13
Servo doorServo;

// ===== RGB LED =====
#define RGB_PIN 48
Adafruit_NeoPixel rgb(1, RGB_PIN, NEO_GRB + NEO_KHZ800);

// ===== Botones (a GND, con pullup interno) =====
#define BTN_LOGIN    1
#define BTN_REGISTER 2
#define BTN_CANCEL   3

unsigned long lastDebounce[3] = {0, 0, 0};

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  rgb.setPixelColor(0, rgb.Color(r, g, b));
  rgb.show();
}

void lcdLines(const char* line1, const char* line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

String getUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

bool postJson(String path, String payload, String& response, int timeoutMs) {
  HTTPClient http;
  String url = String(PC_URL) + path;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(timeoutMs);
  int code = http.POST(payload);
  if (code > 0) response = http.getString();
  http.end();
  return code > 0;
}

void openDoor() {
  doorServo.write(90);
  setRGB(0, 255, 0);
  delay(4000);
  doorServo.write(0);
}

void showResult(String resp) {
  bool authorized = resp.indexOf("\"authorized\":true") >= 0;
  bool registered = resp.indexOf("\"registered\":true") >= 0;
  bool nextStepRfid = resp.indexOf("\"phase\":\"register_rfid\"") >= 0 ||
                      resp.indexOf("\"phase\":\"verify_rfid\"") >= 0;
  bool cancelled = resp.indexOf("cancelada") >= 0;

  String name = "Sistema";
  int n1 = resp.indexOf("\"name\":\"");
  if (n1 >= 0) {
    int n2 = resp.indexOf("\"", n1 + 8);
    name = resp.substring(n1 + 8, n2);
  }

  if (nextStepRfid) {
    setRGB(255, 165, 0);
    lcdLines("Acerca tarjeta", "para confirmar...");
  } else if (authorized && registered) {
    setRGB(0, 255, 0);
    lcdLines("REGISTRADO", name.c_str());
    delay(3000);
    openDoor();
  } else if (authorized) {
    setRGB(0, 255, 0);
    lcdLines("ACCESO CONCEDIDO", name.c_str());
    openDoor();
  } else {
    setRGB(255, 0, 0);
    lcdLines("ACCESO DENEGADO", name.c_str());
    delay(4000);
  }
}

void sendAction(String action, String uid) {
  String payload = "{\"action\":\"" + action + "\"";
  if (uid.length()) payload += ",\"uid\":\"" + uid + "\"";
  payload += "}";

  String resp = "";
  if (postJson("/api/esp/event", payload, resp, 45000)) {
    showResult(resp);
  } else {
    setRGB(255, 0, 0);
    lcdLines("PC no disponible", "Verifica la red");
  }
}

void checkRFID() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;
  String uid = getUID();
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  setRGB(0, 100, 255);
  lcdLines("Tarjeta leida", "Verificando rostro...");
  sendAction("rfid", uid);
}

void checkButtons() {
  struct { int pin; String action; const char* lcd1; } btns[3] = {
    {BTN_LOGIN, "login", "Verificando..."},
    {BTN_REGISTER, "register", "Mire a la camara"},
    {BTN_CANCEL, "cancel", "Cancelando..."}
  };

  for (int i = 0; i < 3; i++) {
    if (digitalRead(btns[i].pin) == LOW) {
      if (millis() - lastDebounce[i] > 300) {
        lastDebounce[i] = millis();
        lcdLines(btns[i].lcd1, "");
        sendAction(btns[i].action, "");
      }
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(BTN_LOGIN, INPUT_PULLUP);
  pinMode(BTN_REGISTER, INPUT_PULLUP);
  pinMode(BTN_CANCEL, INPUT_PULLUP);

  rgb.begin();
  rgb.setBrightness(50);
  setRGB(0, 0, 255);

  doorServo.attach(SERVO_PIN);
  doorServo.write(0);

  SPI.begin(RFID_SCK, RFID_MISO, RFID_MOSI, RFID_SS);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);

  Wire.begin(21, 18);
  lcd.begin(16, 2);
  lcd.backlight();
  lcdLines("Iniciando...", "");

  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    setRGB(0, 255, 0);
    String pcLine = "PC: " + String(PC_URL).substring(7);
    lcdLines("IoT Security", pcLine.c_str());
  } else {
    setRGB(255, 0, 0);
    lcdLines("WiFi ERROR", "UTH Choluteca");
  }

  delay(2000);
  lcdLines("Sistema listo", "TARJETA/LOGIN");
}

void loop() {
  checkButtons();
  checkRFID();
  delay(50);
}
