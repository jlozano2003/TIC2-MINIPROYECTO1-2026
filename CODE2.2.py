import sys
import numpy as np
import matplotlib.ticker as ticker
from scipy.signal import convolve2d
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import ListedColormap
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
import serial # <-- LIBRERÍA PARA ARDUINO

class PvZAutomataApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plantas vs Zombies - Cellular Automata")
        self.setGeometry(100, 100, 900, 650)

        # Configurar conexión con Arduino (¡Cambia COM7 por tu puerto!)
        try:
            self.arduino = serial.Serial('COM7', 9600, timeout=0.1)
            print("Arduino conectado exitosamente.")
        except:
            print("Arduino no detectado. El juego funcionará sin hardware.")
            self.arduino = None

        # Variables del sistema
        self.grid_size = 50
        self.is_playing = False
        
        # Variables de tiempo (Ciclo Día/Noche)
        self.ciclos = 0
        self.es_dia = True
        
        # Kernel para vecindad 3x3
        self.kernel = np.array([[1, 1, 1],
                                [1, 0, 1],
                                [1, 1, 1]])

        # Configuración visual (0: Vacío, 1: Planta, 2: Zombie, 3: Sol)
        self.cmap = ListedColormap(['#FFFFFF', '#4CAF50', '#9C27B0', '#FFEB3B'])

        # Configuración de la interfaz
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QHBoxLayout(self.main_widget)

        self.controls_layout = QVBoxLayout()
        self.layout.addLayout(self.controls_layout, 1)
        self.canvas_layout = QVBoxLayout()
        self.layout.addLayout(self.canvas_layout, 3)

        self.setup_controls()
        self.setup_canvas()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.update_speed(200)

        self.reset_game()

    def setup_controls(self):
        self.btn_play = QPushButton("▶ Iniciar / Pausar")
        self.btn_play.clicked.connect(self.toggle_play)
        self.controls_layout.addWidget(self.btn_play)

        self.btn_reset = QPushButton("🔄 Reiniciar Tablero")
        self.btn_reset.clicked.connect(self.reset_game)
        self.controls_layout.addWidget(self.btn_reset)

        self.controls_layout.addWidget(QLabel("Tamaño de Cuadrícula:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(25, 100) # Mínimo 25 para las bombas de 21x21
        self.slider_size.setValue(self.grid_size)
        self.slider_size.valueChanged.connect(self.change_size)
        self.controls_layout.addWidget(self.slider_size)

        self.controls_layout.addWidget(QLabel("Velocidad de Actualización:"))
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(50, 1000)
        self.slider_speed.setValue(200)
        self.slider_speed.setInvertedAppearance(True)
        self.slider_speed.valueChanged.connect(self.update_speed)
        self.controls_layout.addWidget(self.slider_speed)

        # --- Indicador de Día y Noche ---
        self.lbl_fase = QLabel("Fase: DÍA ☀️")
        self.lbl_fase.setStyleSheet("color: #FBC02D; font-weight: bold; font-size: 16px; margin-top: 10px;")
        self.controls_layout.addWidget(self.lbl_fase)

        self.lbl_plantas = QLabel("Plantas: 0")
        self.lbl_plantas.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        self.controls_layout.addWidget(self.lbl_plantas)

        self.lbl_zombies = QLabel("Zombies: 0")
        self.lbl_zombies.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 14px;")
        self.controls_layout.addWidget(self.lbl_zombies)

        self.lbl_soles = QLabel("Soles: 0")
        self.lbl_soles.setStyleSheet("color: #FBC02D; font-weight: bold; font-size: 14px;")
        self.controls_layout.addWidget(self.lbl_soles)

        # --- Indicador de Eventos / Arduino ---
        self.lbl_evento = QLabel("Evento: ---")
        self.lbl_evento.setStyleSheet("color: #607D8B; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.controls_layout.addWidget(self.lbl_evento)

        self.controls_layout.addWidget(QLabel("Dominio del Tablero:"))
        self.status_indicator = QFrame()
        self.status_indicator.setFixedHeight(30)
        self.controls_layout.addWidget(self.status_indicator)
        self.controls_layout.addStretch()

    def setup_canvas(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.canvas_layout.addWidget(self.canvas)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start()
            self.btn_play.setText("⏸ Pausar")
        else:
            self.timer.stop()
            self.btn_play.setText("▶ Reanudar")

    def update_speed(self, value):
        self.timer.setInterval(value)

    def change_size(self, value):
        self.grid_size = value
        self.reset_game()

    def reset_game(self):
        # [Vacío, Plantas, Zombies, Soles]
        probs = [0.10, 0.35, 0.35, 0.20] # Parámetros balanceados
        self.S = np.random.choice([0, 1, 2, 3], size=(self.grid_size, self.grid_size), p=probs)
        self.T = np.ones((self.grid_size, self.grid_size), dtype=int) 
        self.HP = np.zeros((self.grid_size, self.grid_size), dtype=int)
        self.E = np.zeros((self.grid_size, self.grid_size), dtype=int) 
        self.A = np.zeros((self.grid_size, self.grid_size), dtype=int) 

        self.HP[self.S == 1] = 100 
        self.HP[self.S == 2] = 100 

        # Reiniciar variables de tiempo
        self.ciclos = 0
        self.es_dia = True
        self.lbl_fase.setText("Fase: DÍA ☀️")
        self.lbl_fase.setStyleSheet("color: #FBC02D; font-weight: bold; font-size: 16px; margin-top: 10px;")

        self.ax.clear()
        self.img = self.ax.imshow(self.S, cmap=self.cmap, vmin=0, vmax=3, interpolation='nearest')
        self.ax.set_axis_on()
        self.ax.xaxis.set_major_locator(ticker.NullLocator())
        self.ax.yaxis.set_major_locator(ticker.NullLocator())
        self.ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.ax.grid(True, which='minor', color='#DDDDDD', linestyle='-', linewidth=0.3)
        self.update_ui()

    def limpiar_evento(self):
        self.lbl_evento.setText("Evento: ---")
        self.lbl_evento.setStyleSheet("color: #607D8B; font-weight: bold; font-size: 14px; margin-top: 10px;")

    def bomba_solar(self):
        for _ in range(3):
            r = np.random.randint(0, max(1, self.grid_size - 21))
            c = np.random.randint(0, max(1, self.grid_size - 21))
            zona_S = self.S[r:r+21, c:c+21]
            if 3 in zona_S:
                M_plantas_zona = (zona_S == 1)
                self.E[r:r+21, c:c+21][M_plantas_zona] += 3
        
        # Mostrar en UI y limpiar en 3 segundos
        self.lbl_evento.setText("Evento: ☀️ ¡BOMBA SOLAR!")
        self.lbl_evento.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 14px; margin-top: 10px;")
        QTimer.singleShot(3000, self.limpiar_evento)
        
        self.update_ui()

    def venganza_zombie(self):
        r = np.random.randint(0, max(1, self.grid_size - 21))
        c = np.random.randint(0, max(1, self.grid_size - 21))
        self.S[r:r+21, c:c+21] = 0
        
        # Mostrar en UI y limpiar en 3 segundos
        self.lbl_evento.setText("Evento: 💀 ¡VENGANZA DR. ZOMBIE!")
        self.lbl_evento.setStyleSheet("color: #E91E63; font-weight: bold; font-size: 14px; margin-top: 10px;")
        QTimer.singleShot(3000, self.limpiar_evento)
        
        self.update_ui()

    def update_game(self):
        self.ciclos += 1
        if self.ciclos % 40 == 0:  
            self.es_dia = not self.es_dia
            if self.es_dia:
                self.lbl_fase.setText("Fase: DÍA ☀️")
                self.lbl_fase.setStyleSheet("color: #FBC02D; font-weight: bold; font-size: 16px; margin-top: 10px;")
            else:
                self.lbl_fase.setText("Fase: NOCHE 🌙")
                self.lbl_fase.setStyleSheet("color: #3F51B5; font-weight: bold; font-size: 16px; margin-top: 10px;")

        if self.arduino and self.arduino.in_waiting > 0:
            cmd = self.arduino.readline().decode().strip()
            if cmd == "B-1":
                self.bomba_solar()
            elif cmd == "B-2":
                self.venganza_zombie()

        M_empty = (self.S == 0)
        M_plant = (self.S == 1)
        M_zombie = (self.S == 2)
        M_sun = (self.S == 3)

        M_p_norm = M_plant & ((self.T == 1) | (self.T == 3)) 
        M_p_evol = M_plant & ((self.T == 2) | (self.T == 4)) 
        M_z_norm = M_zombie & (self.T == 1) 
        M_z_evol = M_zombie & (self.T == 2) 

        N_plant = convolve2d(M_plant, self.kernel, mode='same', boundary='wrap')
        N_zombie = convolve2d(M_zombie, self.kernel, mode='same', boundary='wrap')
        N_sun = convolve2d(M_sun, self.kernel, mode='same', boundary='wrap')
        N_p_norm = convolve2d(M_p_norm, self.kernel, mode='same', boundary='wrap')
        N_z_norm = convolve2d(M_z_norm, self.kernel, mode='same', boundary='wrap')
        N_z_evol = convolve2d(M_z_evol, self.kernel, mode='same', boundary='wrap')

        new_S, new_T, new_HP, new_E, new_A = self.S.copy(), self.T.copy(), self.HP.copy(), self.E.copy(), self.A.copy()

        # Daño a Plantas
        dmg_from_z_norm = np.where(N_zombie >= 3, 15, 10) * N_z_norm
        dmg_from_z_evol = 30 * N_z_evol
        new_HP[M_plant] -= (dmg_from_z_norm + dmg_from_z_evol)[M_plant]
        new_E[M_plant] += N_sun[M_plant]

        # Daño a Zombies por Plantas Normales
        dmg_from_p_norm = np.where(N_plant >= 3, 10, 5) * N_p_norm
        new_HP[M_zombie] -= dmg_from_p_norm[M_zombie]

        # --- NUEVO REQUISITO: Daño de Guisantralladora/Gasoseta (Hasta 3 zombies) ---
        evolved_plants_y, evolved_plants_x = np.where(M_p_evol)
        for y, x in zip(evolved_plants_y, evolved_plants_x):
            # Obtener vecinos conectados por los bordes (Toroidal)
            neighbors_coords = [
                ((y-1)%self.grid_size, (x-1)%self.grid_size), ((y-1)%self.grid_size, x), ((y-1)%self.grid_size, (x+1)%self.grid_size),
                (y, (x-1)%self.grid_size),                                               (y, (x+1)%self.grid_size),
                ((y+1)%self.grid_size, (x-1)%self.grid_size), ((y+1)%self.grid_size, x), ((y+1)%self.grid_size, (x+1)%self.grid_size)
            ]
            # Filtrar solo los vecinos que sean zombies
            zombie_coords = [(ny, nx) for ny, nx in neighbors_coords if self.S[ny, nx] == 2]
            
            if zombie_coords:
                # Elegir aleatoriamente un MÁXIMO de 3 zombies para atacar
                np.random.shuffle(zombie_coords)
                for ny, nx in zombie_coords[:3]:
                    new_HP[ny, nx] -= 20
        # -----------------------------------------------------------------------------

        plants_killed = M_plant & (new_HP <= 0)
        N_plants_killed = convolve2d(plants_killed, self.kernel, mode='same', boundary='wrap')
        new_E[M_zombie] += N_plants_killed[M_zombie]

        new_A[M_sun] += 1
        suns_consumed = M_sun & (N_plant > 0)
        suns_expired = M_sun & (new_A >= 5)
        new_S[suns_consumed | suns_expired] = 0

        dead_entities = (M_plant | M_zombie) & (new_HP <= 0)
        new_S[dead_entities] = 0

        plant_evolve = M_plant & (~dead_entities) & (new_E >= 5) & ((self.T == 1) | (self.T == 3))
        new_T[plant_evolve] += 1 
        new_HP[plant_evolve] = 250
        
        zombie_evolve = M_zombie & (~dead_entities) & (new_E >= 6) & (self.T == 1)
        new_T[zombie_evolve] = 2
        new_HP[zombie_evolve] = 300
        new_E[zombie_evolve] = 0

        M_new_empty = (new_S == 0)

        if self.es_dia:
            spawn_day = M_new_empty & (N_sun >= 3)
            new_S[spawn_day], new_T[spawn_day], new_HP[spawn_day], new_E[spawn_day] = 1, 1, 100, 0
            M_new_empty &= ~spawn_day
        else:
            spawn_night = M_new_empty & ((N_sun == 1) | (N_sun == 2))
            rand_vals = np.random.rand(*self.S.shape)
            
            spawn_seta = spawn_night & (rand_vals < 0.10)
            new_S[spawn_seta], new_T[spawn_seta], new_HP[spawn_seta], new_E[spawn_seta] = 1, 3, 100, 0
            
            spawn_zombie = spawn_night & (rand_vals >= 0.10) & (rand_vals < 0.40)
            new_S[spawn_zombie], new_T[spawn_zombie], new_HP[spawn_zombie], new_E[spawn_zombie] = 2, 1, 100, 0
            
            M_new_empty &= ~(spawn_seta | spawn_zombie)

        spawn_sun = M_new_empty & (np.random.rand(*self.S.shape) < 0.30)
        new_S[spawn_sun] = 3
        new_A[spawn_sun] = 0

        self.S, self.T, self.HP, self.E, self.A = new_S, new_T, new_HP, new_E, new_A
        self.update_ui()

    def update_ui(self):
        self.img.set_data(self.S)
        self.canvas.draw()

        c_plantas = np.sum(self.S == 1)
        c_zombies = np.sum(self.S == 2)
        c_soles = np.sum(self.S == 3)

        self.lbl_plantas.setText(f"Plantas: {c_plantas}")
        self.lbl_zombies.setText(f"Zombies: {c_zombies}")
        self.lbl_soles.setText(f"Soles: {c_soles}")

        if self.arduino:
            msg = f"A-P{c_plantas:03d}-Z{c_zombies:03d}\n"
            self.arduino.write(msg.encode())

        if c_plantas > c_zombies:
            color = "#4CAF50" 
        elif c_zombies > c_plantas:
            color = "#9C27B0" 
        else:
            color = "#9E9E9E" 

        self.status_indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

        # --- NUEVO REQUISITO: Condición de Fin de Juego ---
        if self.is_playing:
            if c_plantas == 0 and c_zombies > 0:
                self.toggle_play() # Pausa el juego
                QApplication.beep() # Efecto de sonido del sistema
                QMessageBox.information(self, "¡Fin del Juego!", "¡Los Zombies han dominado el tablero! 🧠\n\nPresiona 'Reiniciar Tablero' para jugar de nuevo.")
            
            elif c_zombies == 0 and c_plantas > 0:
                self.toggle_play()
                QApplication.beep()
                QMessageBox.information(self, "¡Fin del Juego!", "¡Las Plantas han defendido el jardín exitosamente! 🌻\n\nPresiona 'Reiniciar Tablero' para jugar de nuevo.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PvZAutomataApp()
    window.show()
    sys.exit(app.exec())