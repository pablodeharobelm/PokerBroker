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
from interfaz_online import PanelOnline

from construccion_mesa import ConstruccionMesa
from presentacion_mesa import PresentacionMesa

class VentanaMesaPoker(ControlMesa, ConstruccionMesa, PresentacionMesa, QMainWindow):
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

        self.tab_online = PanelOnline()
        destinos = {"mesa": self.tab_mesa, "stats": self.tab_stats, "historial": self.tab_historial, "online": self.tab_online}
        self.tab_inicio = crear_inicio(lambda destino: self.tabs.setCurrentWidget(destinos[destino]))
        self.tabs.addTab(self.tab_inicio, "PokerBroker · Inicio")
        self.tabs.addTab(self.tab_mesa, "Mesa de práctica")
        self.tabs.addTab(self.tab_stats, "Estadísticas")
        self.tabs.addTab(self.tab_historial, "Historial")
        self.tabs.addTab(self.tab_online, "Amigos · Local")

        self.init_ui()
        self.init_stats_ui()
        self.construir_asientos()
        self.iniciar_nueva_mano()
        self.tabs.currentChanged.connect(self._cambiar_seccion)

    def _cambiar_seccion(self, _indice):
        self._refrescar_mesa()

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
        self.tab_online.cerrar()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaMesaPoker()
    ventana.show()
    sys.exit(app.exec())
