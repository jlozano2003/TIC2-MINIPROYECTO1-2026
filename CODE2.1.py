import sys
import numpy as np
import matplotlib.ticker as ticker # (1) NUEVA IMPORTACIÓN
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, QFrame)
from PyQt6.QtCore import Qt, QTimer

class GameOfLifeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Game of Life - PyQt6 & Matplotlib")
        self.setGeometry(100, 100, 800, 600)

        # Variables del sistema
        self.grid_size = 50
        self.density = 0.2
        self.is_playing = False
        self.grid = np.zeros((self.grid_size, self.grid_size))
        self.prev_population = 0

        # Configuración de la interfaz
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QHBoxLayout(self.main_widget)

        # Panel izquierdo (Controles)
        self.controls_layout = QVBoxLayout()
        self.layout.addLayout(self.controls_layout, 1)

        # Panel derecho (Matplotlib)
        self.canvas_layout = QVBoxLayout()
        self.layout.addLayout(self.canvas_layout, 3)

        self.setup_controls()
        self.setup_canvas()

        # QTimer para la actualización en tiempo real
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.update_speed(100) # 100 ms por defecto

        # Inicializar el primer tablero
        self.reset_game()

    def setup_controls(self):
        # Botón Play/Pause
        self.btn_play = QPushButton("▶ Iniciar / Pausar")
        self.btn_play.clicked.connect(self.toggle_play)
        self.controls_layout.addWidget(self.btn_play)

        # Botón Reinicio
        self.btn_reset = QPushButton("🔄 Reiniciar Tablero")
        self.btn_reset.clicked.connect(self.reset_game)
        self.controls_layout.addWidget(self.btn_reset)

        # Slider: Tamaño de cuadrícula
        self.controls_layout.addWidget(QLabel("Tamaño de Cuadrícula:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(10, 150)
        self.slider_size.setValue(self.grid_size)
        self.slider_size.valueChanged.connect(self.change_size)
        self.controls_layout.addWidget(self.slider_size)

        # Slider: Velocidad
        self.controls_layout.addWidget(QLabel("Velocidad de Actualización:"))
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(10, 1000) # de 10ms a 1000ms
        self.slider_speed.setValue(100)
        self.slider_speed.setInvertedAppearance(True) # Más a la derecha = menos ms = más rápido
        self.slider_speed.valueChanged.connect(self.update_speed)
        self.controls_layout.addWidget(self.slider_speed)

        # Slider: Densidad Inicial
        self.controls_layout.addWidget(QLabel("Densidad Inicial de Células:"))
        self.slider_density = QSlider(Qt.Orientation.Horizontal)
        self.slider_density.setRange(1, 99)
        self.slider_density.setValue(int(self.density * 100))
        self.slider_density.valueChanged.connect(self.update_density)
        self.controls_layout.addWidget(self.slider_density)

        # Contador de células
        self.lbl_counter = QLabel("Células Vivas: 0")
        self.lbl_counter.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 20px;")
        self.controls_layout.addWidget(self.lbl_counter)

        # Indicador visual de estado (Comportamiento global)
        self.controls_layout.addWidget(QLabel("Estado Global:"))
        self.status_indicator = QFrame()
        self.status_indicator.setFixedHeight(30)
        self.status_indicator.setStyleSheet("background-color: gray; border-radius: 5px;")
        self.controls_layout.addWidget(self.status_indicator)
        self.controls_layout.addStretch()

    def setup_canvas(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # (2) CAMBIO: En lugar de 'off', ocultamos marcas mayores inicialmente
        self.ax.xaxis.set_major_locator(ticker.NullLocator())
        self.ax.yaxis.set_major_locator(ticker.NullLocator())

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

    def update_density(self, value):
        self.density = value / 100.0

    def reset_game(self):
        # Generar tablero aleatorio según la densidad
        self.grid = np.random.choice([0, 1], 
                                     size=(self.grid_size, self.grid_size), 
                                     p=[1 - self.density, self.density])
        self.prev_population = np.sum(self.grid)

        # Limpiar y recrear el gráfico entero por si el tamaño cambió
        self.ax.clear()

        self.img = self.ax.imshow(self.grid, cmap='binary', interpolation='nearest')

        # (3) CAMBIO: === CONFIGURACIÓN DE LA CUADRÍCULA ===
        self.ax.set_axis_on() # Asegurar que los ejes estén activados

        # Ocultar marcas mayores y sus etiquetas
        self.ax.xaxis.set_major_locator(ticker.NullLocator())
        self.ax.yaxis.set_major_locator(ticker.NullLocator())

        # Configurar marcas menores para las líneas de la cuadrícula a 0.5 unidades
        # Esto coloca las líneas entre los píxeles (centros en enteros 0, 1, 2...)
        self.ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.5))

        # Dibujar la cuadrícula en las marcas menores
        # Usar grosor muy fino y color sutil (DDDDDD es gris muy claro)
        self.ax.grid(True, which='minor', color='#DDDDDD', linestyle='-', linewidth=0.3)
        # ===============================================

        self.update_ui()

    def update_game(self):
        # Contar vecinos vivos usando np.roll para simular un toroide
        neighbors = (np.roll(self.grid, 1, axis=0) + np.roll(self.grid, -1, axis=0) +
                     np.roll(self.grid, 1, axis=1) + np.roll(self.grid, -1, axis=1) +
                     np.roll(np.roll(self.grid, 1, axis=0), 1, axis=1) +
                     np.roll(np.roll(self.grid, -1, axis=0), -1, axis=1) +
                     np.roll(np.roll(self.grid, 1, axis=0), -1, axis=1) +
                     np.roll(np.roll(self.grid, -1, axis=0), 1, axis=1))

        # Aplicar reglas de Conway de manera simultánea
        new_grid = np.copy(self.grid)

        # Supervivencia (2 o 3 vecinos) y Nacimiento (3 vecinos)
        new_grid = np.where((self.grid == 1) & ((neighbors < 2) | (neighbors > 3)), 0, new_grid)
        new_grid = np.where((self.grid == 0) & (neighbors == 3), 1, new_grid)

        self.grid = new_grid
        self.update_ui()

    def update_ui(self):
        # 1. Actualizar dibujo en Matplotlib
        self.img.set_data(self.grid)
        self.canvas.draw()

        # 2. Actualizar contador
        current_population = np.sum(self.grid)
        self.lbl_counter.setText(f"Células Vivas: {current_population}")

        # 3. Actualizar elemento visual de estado global
        if current_population > self.prev_population:
            color = "#4CAF50"  # Verde (Crecimiento)
        elif current_population < self.prev_population:
            color = "#F44336"  # Rojo (Decrecimiento)
        else:
            color = "#FFEB3B"  # Amarillo (Estabilidad)
            if current_population == 0:
                color = "#212121" # Negro (Extinción)

        self.status_indicator.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.prev_population = current_population

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GameOfLifeApp()
    window.show()
    sys.exit(app.exec())