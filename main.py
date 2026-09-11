import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QHBoxLayout, QVBoxLayout, QPushButton, QSlider,
                               QTabWidget, QMessageBox, QCheckBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

# Importaciones de los nuevos componentes fragmentados y estables
from componentes_dibujo import MesaDibujo, FichasBote
from interfaz_estadisticas import refrescar_interfaz_estadisticas
from interfaz_historial import refrescar_historial
from logica_poker import Usuario, BaseDatosLocal
import componentes_visuales as cv
import estilos as est

from control_mesa import ControlMesa
from equity import ServicioEquity
from sesion_guardada import ArchivoSesion
from pathlib import Path
from interfaz_inicio import crear_inicio

class VentanaMesaPoker(ControlMesa, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poker Trainer - Mesa de práctica")
        self.setFixedSize(1020, 740)

        self.jugador = Usuario("Finwa22", banco_inicial=10000)
        self.sesion = self.jugador.iniciar_sesion_mesa(2000)

        self.datos_rivales = [
            {"nombre": "peco246", "fichas": "7,100", "x": 450, "y": 70},
            {"nombre": "Breta232", "fichas": "9,921", "x": 800, "y": 120},
            {"nombre": "Davidkim", "fichas": "10,884", "x": 800, "y": 300},
            {"nombre": "_Yurec0816", "fichas": "2,850", "x": 40, "y": 300},
            {"nombre": "FAKEL382", "fichas": "10,176", "x": 40, "y": 120},
        ]

        self.mis_cartas_actuales = []
        self.fase_actual = 0
        self.bote_actual = 0
        self.apuesta_a_pagar = 0
        self.cantidad_a_apostar = 0
        self.asientos_visuales = {}

        self.bd_local = BaseDatosLocal()
        self.archivo_sesion = ArchivoSesion(Path(self.bd_local.ruta_archivo).with_suffix(".sesion.json"))
        self.sesion_bloqueada = False
        self.servicio_equity = ServicioEquity(self)
        self.servicio_equity.resultado.connect(self._recibir_equity)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(est.ESTILO_PESTANAS)
        self.setCentralWidget(self.tabs)

        self.tab_mesa = MesaDibujo()
        self.tab_stats = QWidget()
        self.tab_historial = QWidget()

        destinos = {"mesa": self.tab_mesa, "stats": self.tab_stats, "historial": self.tab_historial}
        self.tab_inicio = crear_inicio(lambda destino: self.tabs.setCurrentWidget(destinos[destino]))
        self.tabs.addTab(self.tab_inicio, "PokerBroker · Inicio")
        self.tabs.addTab(self.tab_mesa, "Mesa de práctica")
        self.tabs.addTab(self.tab_stats, "Estadísticas")
        self.tabs.addTab(self.tab_historial, "Historial")

        self.init_ui()
        self.init_stats_ui()
        self.construir_asientos()
        self.iniciar_nueva_mano()
        self.tabs.currentChanged.connect(self._cambiar_seccion)

    def _cambiar_seccion(self, _indice):
        self._refrescar_mesa()

    def init_ui(self):
        """Distribuye la interfaz visual dividiendo el panel inferior en dos columnas laterales."""
        layout_principal = QVBoxLayout(self.tab_mesa)
        layout_principal.setContentsMargins(15, 15, 15, 15)

        self.lbl_bote = QLabel("BOTE: 0", self.tab_mesa)
        self.lbl_bote.setFixedSize(180, 32)
        self.lbl_bote.move(410, 155)
        self.lbl_bote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bote.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_bote.setStyleSheet(est.ESTILO_BOTE)
        self.lbl_bote.setToolTip("Las pilas representan el tamaño aproximado del bote. El importe exacto es el de esta etiqueta.")
        self.fichas_bote = FichasBote(self.tab_mesa)
        self.fichas_bote.move(300, 125)

        self.widget_centro = QWidget(self.tab_mesa)
        self.widget_centro.setFixedSize(450, 120)
        self.widget_centro.move(275, 195)
        self.layout_centro = QHBoxLayout(self.widget_centro)
        self.layout_centro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_centro.setSpacing(8)

        self.lbl_resultado_mano = QLabel("", self.tab_mesa)
        self.lbl_resultado_mano.setFixedSize(500, 30)
        self.lbl_resultado_mano.move(250, 325)
        self.lbl_resultado_mano.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_resultado_mano.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_resultado_mano.setStyleSheet("color: #888888; background: transparent; border: none;")

        layout_principal.addStretch()

        widget_split_inferior = QWidget()
        layout_split = QHBoxLayout(widget_split_inferior)
        layout_split.setContentsMargins(0, 0, 0, 0)
        layout_split.setSpacing(40)

        widget_columna_izquierda = QWidget()
        layout_col_izq = QVBoxLayout(widget_columna_izquierda)
        layout_col_izq.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_col_izq.setSpacing(5)

        self.panel_mio = QWidget()
        self.panel_mio.setStyleSheet("background-color: rgba(30, 30, 30, 230); color: white; border: 2px solid #555555; border-radius: 8px; padding: 5px;")
        self.panel_mio.setFixedSize(140, 55)

        layout_texto_mio = QVBoxLayout(self.panel_mio)
        layout_texto_mio.setContentsMargins(5, 2, 5, 2)
        layout_texto_mio.setSpacing(2)

        self.lbl_nombre_propio = QLabel("Finwa22 (Tú)")
        self.lbl_nombre_propio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nombre_propio.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lbl_nombre_propio.setStyleSheet("color: #E0E0E0; border: none; background: transparent;")

        self.lbl_fichas_propias = QLabel("2,000")
        self.lbl_fichas_propias.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fichas_propias.setFont(QFont("Arial", 10))
        self.lbl_fichas_propias.setStyleSheet("color: #A0A0A0; border: none; background: transparent;")

        layout_texto_mio.addWidget(self.lbl_nombre_propio)
        layout_texto_mio.addWidget(self.lbl_fichas_propias)
        layout_col_izq.addWidget(self.panel_mio, alignment=Qt.AlignmentFlag.AlignCenter)
        widget_cartas_y_hud = QWidget()
        layout_cartas_y_hud = QHBoxLayout(widget_cartas_y_hud)
        layout_cartas_y_hud.setContentsMargins(0, 0, 0, 0)
        layout_cartas_y_hud.setSpacing(15)

        self.panel_hud_ia = QWidget()
        self.panel_hud_ia.setFixedSize(250, 150)
        self.panel_hud_ia.setStyleSheet("background-color: rgba(12, 12, 12, 245); color: #26e600; border: 1px dashed #444444; border-radius: 6px; padding: 8px;")

        layout_textos_ia = QVBoxLayout(self.panel_hud_ia)
        layout_textos_ia.setContentsMargins(8, 8, 8, 8)
        layout_textos_ia.setSpacing(5)

        self.lbl_hud_posicion = QLabel("POSICIÓN: TBD")
        self.lbl_hud_posicion.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.lbl_hud_posicion.setStyleSheet("color: #26e600;")

        self.lbl_hud_equity = QLabel("JUGADA: Calculando...")
        self.lbl_hud_equity.setStyleSheet("color: #00bfff;")
        self.lbl_hud_equity.setFont(QFont("Consolas", 9, QFont.Weight.Bold))

        self.lbl_hud_consejo = QLabel("CONSEJO: Esperando...")
        self.lbl_hud_consejo.setStyleSheet("color: #EAEAEA;")
        self.lbl_hud_consejo.setFont(QFont("Segoe UI", 9))
        self.lbl_hud_consejo.setWordWrap(True)

        layout_textos_ia.addWidget(self.lbl_hud_posicion)
        layout_textos_ia.addWidget(self.lbl_hud_equity)
        layout_textos_ia.addWidget(self.lbl_hud_consejo)
        layout_textos_ia.addStretch()

        layout_cartas_y_hud.addWidget(self.panel_hud_ia)

        self.widget_cartas_fisicas = QWidget()
        self.layout_mano = QHBoxLayout(self.widget_cartas_fisicas)
        self.layout_mano.setContentsMargins(0, 0, 0, 0)
        self.layout_mano.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_cartas_y_hud.addWidget(self.widget_cartas_fisicas)

        layout_col_izq.addWidget(widget_cartas_y_hud, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_split.addWidget(widget_columna_izquierda)

        widget_columna_derecha = QWidget()
        layout_col_der = QVBoxLayout(widget_columna_derecha)
        layout_col_der.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_col_der.setSpacing(10)

        self.chk_ayudas = QCheckBox("Mostrar ayudas de entrenamiento")
        self.chk_ayudas.setChecked(True)
        self.chk_ayudas.setStyleSheet("color: #eeeeee; font-size: 12px;")
        layout_col_der.addWidget(self.chk_ayudas)
        self.panel_ayudas = QWidget()
        self.panel_ayudas.setFixedSize(475, 150)
        self.panel_ayudas.setStyleSheet("background: #15221f; border: 1px solid #31554a; border-radius: 6px;")
        layout_ayudas = QVBoxLayout(self.panel_ayudas)
        layout_ayudas.setContentsMargins(10, 7, 10, 7)
        layout_ayudas.setSpacing(3)
        self.lbl_ayuda_call = QLabel()
        self.lbl_equity_estimada = QLabel()
        self.lbl_ayuda_proyectos = QLabel()
        self.lbl_ayuda_nota = QLabel()
        for etiqueta in (self.lbl_ayuda_call, self.lbl_equity_estimada, self.lbl_ayuda_proyectos, self.lbl_ayuda_nota):
            etiqueta.setWordWrap(True)
            etiqueta.setStyleSheet("color: #dcebe6; background: transparent; border: none; font-size: 11px;")
            layout_ayudas.addWidget(etiqueta)
        self.lbl_ayuda_call.setStyleSheet("color: #00ffcc; background: transparent; border: none; font-size: 12px; font-weight: bold;")
        layout_col_der.addWidget(self.panel_ayudas)
        self.chk_ayudas.toggled.connect(self.actualizar_ayudas)
        self.chk_ayudas.toggled.connect(lambda _: self._guardar_sesion())

        layout_slider_fila = QHBoxLayout()
        layout_slider_fila.setSpacing(8)

        self.btn_min = QPushButton("Min")
        self.btn_half = QPushButton("1/2 Pot")
        self.btn_pot = QPushButton("Pot")
        self.btn_max = QPushButton("Max")

        for btn in [self.btn_min, self.btn_half, self.btn_pot, self.btn_max]:
            btn.setStyleSheet(est.ESTILO_BOTONES_FIJOS)
            layout_slider_fila.addWidget(btn)

        self.btn_min.clicked.connect(lambda: self.fijar_tamano_apuesta("min"))
        self.btn_half.clicked.connect(lambda: self.fijar_tamano_apuesta("half"))
        self.btn_pot.clicked.connect(lambda: self.fijar_tamano_apuesta("pot"))
        self.btn_max.clicked.connect(lambda: self.fijar_tamano_apuesta("max"))
        layout_col_der.addLayout(layout_slider_fila)
        self.slider_apuestas = QSlider(Qt.Orientation.Horizontal)
        self.slider_apuestas.setFixedWidth(280)
        self.slider_apuestas.setSingleStep(10)
        self.slider_apuestas.setPageStep(50)
        self.slider_apuestas.setStyleSheet(est.ESTILO_SLIDER)
        self.slider_apuestas.valueChanged.connect(self.actualizar_valor_slider)
        layout_col_der.addWidget(self.slider_apuestas, alignment=Qt.AlignmentFlag.AlignCenter)

        layout_botones_fila = QHBoxLayout()
        layout_botones_fila.setSpacing(10)

        self.btn_fold = QPushButton("Fold")
        self.btn_call = QPushButton("Check")
        self.btn_raise = QPushButton("Bet / Raise")

        for btn in [self.btn_fold, self.btn_call, self.btn_raise]:
            btn.setStyleSheet(est.ESTILO_BOTONES_ACCION + """
                QPushButton { font-size: 12px; padding: 10px 8px; min-width: 135px; }
                QPushButton:disabled { background: #333333; color: #777777; border-color: #444444; }
            """)
            layout_botones_fila.addWidget(btn)

        self.btn_call.clicked.connect(self.avanzar_fase_juego)
        self.btn_fold.clicked.connect(self.ejecutar_fold)
        self.btn_raise.clicked.connect(self.ejecutar_apuesta_raise)

        layout_col_der.addLayout(layout_botones_fila)
        layout_split.addWidget(widget_columna_derecha)
        layout_principal.addWidget(widget_split_inferior)

    def init_stats_ui(self):
        """Llama al actualizador del sub-archivo independiente para refrescar las analíticas."""
        refrescar_interfaz_estadisticas(self.tab_stats, self.bd_local)
        refrescar_historial(self.tab_historial, self.bd_local)

    def closeEvent(self, event):
        if not self.sesion_bloqueada and not self._guardar_sesion():
            respuesta = QMessageBox.warning(
                self, "Sesión sin guardar", "No se pudo guardar la sesión actual. ¿Cerrar perdiendo los cambios desde el último guardado?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if respuesta != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        if hasattr(self, "registro_pendiente") and self.motor.terminada and not self.mano_registrada:
            self._finalizar_mano()
            if not self.mano_registrada:
                respuesta = QMessageBox.warning(
                    self, "Mano sin guardar", "El guardado ha fallado. Si cierras, perderás el registro de esta última mano.",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel)
                if respuesta != QMessageBox.StandardButton.Discard:
                    event.ignore()
                    return
        if hasattr(self, "timer_bot"):
            self.timer_bot.stop()
        if hasattr(self, "timer_calle"):
            self.timer_calle.stop()
            self.transicion_calle = None
        self.servicio_equity.cancelar()
        super().closeEvent(event)

    def construir_asientos(self):
        """Inicializa las referencias de los perfiles y crea los letreros de apuestas flotantes."""
        self.lbl_apuestas_bots = {}
        self.lbl_apuesta_propia = QLabel("", self.tab_mesa)
        self.lbl_apuesta_propia.setGeometry(330, 380, 150, 42)
        self.lbl_apuesta_propia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for i, r in enumerate(self.datos_rivales):
            etiquetas = cv.crear_cuadro_perfil(self.tab_mesa, r["nombre"], r["fichas"], r["x"], r["y"])
            self.asientos_visuales[i] = etiquetas

            lbl_apuesta = QLabel("", self.tab_mesa)
            lbl_apuesta.setFixedSize(150, 42)
            lbl_apuesta.move(r["x"] - 5, r["y"] + 58)
            if i == 0:
                lbl_apuesta.move(r["x"] + 150, r["y"] + 5)
            lbl_apuesta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_apuesta.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_apuesta.setStyleSheet("color: #00ffcc; background-color: rgba(15, 15, 15, 220); border: 1px solid #333333; border-radius: 4px;")
            lbl_apuesta.hide()
            self.lbl_apuestas_bots[i] = lbl_apuesta

        self.asientos_visuales["nombre"] = self.lbl_nombre_propio
        self.asientos_visuales["fichas"] = self.lbl_fichas_propias

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaMesaPoker()
    ventana.show()
    sys.exit(app.exec())
