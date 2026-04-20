// --- CONFIGURACIÓN DEL JUEGO ---
const int NUM_POSICIONES = 6; // Configurable entre 4 y 6

// ¡CAMBIAMOS EL PIN 1 POR EL A1 PARA MATAR EL FANTASMA!
const int pinesBotones[NUM_POSICIONES] = {0, 2, 3, 4, 5, 6}; 
const int pinesLEDs[NUM_POSICIONES] = {8, 9, 10, 11, 12, 13};
const int pinBuzzer = 7;

// Variables de estado del juego
int indiceBomba;
bool botonesPresionados[NUM_POSICIONES];
int aciertos = 0;
int rachaAciertos = 0; 
bool juegoActivo = false;

// --- DIFICULTAD: TIEMPO ---
unsigned long tiempoUltimaAccion;
// 10 segundos (10000 ms)
const unsigned long TIEMPO_MAXIMO = 10000; 

void setup() {
  Serial.begin(9600);

  // Inicializar pines
  for (int i = 0; i < NUM_POSICIONES; i++) {
    pinMode(pinesBotones[i], INPUT_PULLUP);
    pinMode(pinesLEDs[i], OUTPUT);
    digitalWrite(pinesLEDs[i], LOW);
  }
  pinMode(pinBuzzer, OUTPUT);

  // Generación de semilla aleatoria
  randomSeed(analogRead(0)); 

  iniciarRonda();
}

void loop() {
  if (!juegoActivo) {
    for (int i = 0; i < NUM_POSICIONES; i++) {
      if (digitalRead(pinesBotones[i]) == LOW) { 
        delay(200); 
        iniciarRonda();
        break;
      }
    }
    return; 
  }

  // Lógica de dificultad por tiempo límite
  if (millis() - tiempoUltimaAccion > TIEMPO_MAXIMO) {
    Serial.println("\n¡TIEMPO AGOTADO! Te demoraste mucho y la bomba explotó.");
    Serial.println("La ronda ha terminado.");
    secuenciaDerrota(); 
    rachaAciertos = 0;
    juegoActivo = false;
    return; 
  }

  // Revisar botones
  for (int i = 0; i < NUM_POSICIONES; i++) {
    if (digitalRead(pinesBotones[i]) == LOW && !botonesPresionados[i]) {
      delay(50); // Antirrebote

      if (digitalRead(pinesBotones[i]) == LOW) {
        botonesPresionados[i] = true;
        procesarJugada(i);
      }
    }
  }
}

void iniciarRonda() {
  Serial.println("\n--- NUEVA RONDA: BOWSER'S BIG BLAST ---");
  Serial.println("¡Tienes 10 segundos para elegir un botón seguro!");

  aciertos = 0;
  juegoActivo = true;
  for (int i = 0; i < NUM_POSICIONES; i++) {
    botonesPresionados[i] = false;
    digitalWrite(pinesLEDs[i], LOW); 
  }

  indiceBomba = random(NUM_POSICIONES);
  tiempoUltimaAccion = millis();
}

void procesarJugada(int posicionElegida) {
  if (posicionElegida == indiceBomba) {
    Serial.println("¡BOOOOOOM! Presionaste la bomba.");
    Serial.println("La ronda ha terminado.");

    secuenciaDerrota();
    rachaAciertos = 0; 
    juegoActivo = false; 

  } else {
    Serial.println("¡Uff! Elección correcta.");
    digitalWrite(pinesLEDs[posicionElegida], HIGH);

    melodiaExito();
    aciertos++;

    // Reiniciamos el temporizador con la jugada válida
    tiempoUltimaAccion = millis(); 

    if (aciertos == NUM_POSICIONES - 1) {
      Serial.println("¡FELICIDADES! Encontraste todos los botones seguros.");
      rachaAciertos++;
      Serial.print("Racha actual: "); Serial.println(rachaAciertos);

      secuenciaVictoria(); 
      juegoActivo = false;
    }
  }
}

// --- FUNCIONES DE EFECTOS ---

void melodiaExito() {
  tone(pinBuzzer, 1000, 100); 
  delay(150);
}

void secuenciaDerrota() {
  tone(pinBuzzer, 200, 500);

  for(int j=0; j<5; j++){
    for (int i = 0; i < NUM_POSICIONES; i++) {
      digitalWrite(pinesLEDs[i], HIGH);
    }
    delay(100);
    for (int i = 0; i < NUM_POSICIONES; i++) {
      digitalWrite(pinesLEDs[i], LOW);
    }
    delay(100);
  }
}

void secuenciaVictoria() {
  tone(pinBuzzer, 523, 150); 
  delay(150);
  tone(pinBuzzer, 659, 150); 
  delay(150);
  tone(pinBuzzer, 784, 150); 
  delay(150);
  tone(pinBuzzer, 1046, 400); 

  for(int j = 0; j < 4; j++){
    for (int i = 0; i < NUM_POSICIONES; i++) {
      digitalWrite(pinesLEDs[i], HIGH);
    }
    delay(150);
    for (int i = 0; i < NUM_POSICIONES; i++) {
      digitalWrite(pinesLEDs[i], LOW);
    }
    delay(150);
  }
}