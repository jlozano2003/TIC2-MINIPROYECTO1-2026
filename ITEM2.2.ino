const int ledPlantas = 6;
const int ledZombies = 9;
const int btnBomba = 5;
const int btnVenganza = 3;

void setup() {
  Serial.begin(9600);
  pinMode(ledPlantas, OUTPUT);
  pinMode(ledZombies, OUTPUT);
  pinMode(btnBomba, INPUT_PULLUP); // Usa resistencias internas
  pinMode(btnVenganza, INPUT_PULLUP);
}

void loop() {
  // 1. LEER DESDE PYTHON (Actualizar LEDs)
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    
    // Validar formato A-PXXX-ZXXX
    if (data.startsWith("A-P") && data.indexOf("-Z") != -1) {
      int pIndex = data.indexOf("P") + 1;
      int zIndex = data.indexOf("Z") + 1;
      
      int numPlantas = data.substring(pIndex, pIndex + 3).toInt();
      int numZombies = data.substring(zIndex, zIndex + 3).toInt();
      
      // Mapear la cantidad (ej. de 0 a 2500 celdas) a brillo PWM (0-255)
      int brilloP = map(constrain(numPlantas, 0, 1000), 0, 1000, 0, 255);
      int brilloZ = map(constrain(numZombies, 0, 1000), 0, 1000, 0, 255);
      
      analogWrite(ledPlantas, brilloP);
      analogWrite(ledZombies, brilloZ);
    }
  }

  // 2. ENVIAR A PYTHON (Botones de habilidades)
  if (digitalRead(btnBomba) == LOW) {
    Serial.println("B-1");
    delay(300); // Anti-rebote
  }
  if (digitalRead(btnVenganza) == LOW) {
    Serial.println("B-2");
    delay(300);
  }
}