"""Cliente de pruebas: dibuja estados recibidos, nunca ejecuta el motor."""
import json
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QLineEdit, QSpinBox)
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtNetwork import QAbstractSocket
from vista_mesa_red import VistaMesaRed


class PanelOnline(QWidget):
    def __init__(self, parent=None, puerto=8765):
        super().__init__(parent)
        self.puerto, self.servidor_local = puerto, None
        self.estado, self.pendiente = None, None
        self.socket = QWebSocket(parent=self)
        self.socket.connected.connect(self._conectado)
        self.socket.textMessageReceived.connect(self._recibir)
        self.socket.disconnected.connect(self._desconectado)
        self.socket.errorOccurred.connect(self._error_conexion)
        self.lobby = QWidget()
        self.lobby.setStyleSheet("QWidget { background: #101512; color: #efe6d2; font-family: 'Segoe UI'; } QPushButton, QLineEdit, QSpinBox { background: #244333; border: 1px solid #465139; border-radius: 6px; padding: 9px; } QPushButton:disabled { color: #788477; } QPushButton:hover { border-color: #cfb477; }")
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self.lobby)
        layout.setContentsMargins(30, 20, 30, 20)
        titulo = QLabel("Amigos · Prueba local")
        titulo.setStyleSheet("font-size: 27px; font-weight: bold;")
        layout.addWidget(titulo)
        self.mensaje = QLabel("Dos ventanas en este ordenador · 2–6 jugadores · 2.000 fichas · Ciegas 20/40")
        self.mensaje.setTextFormat(Qt.TextFormat.PlainText)
        self.mensaje.setWordWrap(True)
        layout.addWidget(self.mensaje)
        fila = QHBoxLayout()
        self.host = QPushButton("Iniciar servidor local")
        self.host.clicked.connect(self._iniciar_servidor)
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Tu apodo")
        self.nombre.setMaxLength(20)
        self.codigo = QLineEdit()
        self.codigo.setPlaceholderText("Código de sala")
        self.codigo.setMaxLength(6)
        self.crear, self.unir = QPushButton("Crear sala"), QPushButton("Unirse")
        self.crear.clicked.connect(lambda: self.conectar("crear"))
        self.unir.clicked.connect(lambda: self.conectar("unir"))
        for widget in (self.host, self.nombre, self.codigo, self.crear, self.unir):
            fila.addWidget(widget)
        layout.addLayout(fila)
        self.sala = QLabel("Sin sala")
        self.sala.setTextFormat(Qt.TextFormat.PlainText)
        self.sala.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.sala)
        self.vista = VistaMesaRed()
        self.vista.accion.connect(self._actuar)
        self.vista.hide()
        self.vista.nueva_mano.connect(lambda: self._enviar("iniciar"))
        pie = QHBoxLayout()
        self.iniciar, self.salir = QPushButton("Iniciar mano"), QPushButton("Salir de la sala")
        self.iniciar.setEnabled(False)
        self.salir.setEnabled(False)
        self.iniciar.clicked.connect(lambda: self._enviar("iniciar"))
        self.salir.clicked.connect(self.socket.close)
        pie.addWidget(self.iniciar)
        pie.addWidget(self.salir)
        layout.addLayout(pie)
        nota = QLabel("Prototipo local: salir cierra la sala. Sin reconexión ni historial online todavía.")
        nota.setStyleSheet("color: #929888; font-size: 11px;")
        layout.addWidget(nota)

        raiz.addWidget(self.lobby)
        raiz.addWidget(self.vista, 1)
        self.sala_mesa = QLabel('', self.vista.tab_mesa)
        self.sala_mesa.setTextFormat(Qt.TextFormat.PlainText)
        self.sala_mesa.setGeometry(15, 4, 360, 24)
        self.sala_mesa.setStyleSheet('color: #aaaaaa; background: transparent; font-size: 11px;')
        self.salir_mesa = QPushButton('Salir de la sala', self.vista.tab_mesa)
        self.salir_mesa.setGeometry(850, 4, 145, 27)
        self.salir_mesa.setStyleSheet('background: #242424; color: #cccccc; border: 1px solid #555555; border-radius: 5px;')
        self.salir_mesa.setToolTip('En esta prueba local, salir cierra la sala para todos.')
        self.salir_mesa.clicked.connect(self.socket.close)

    def _iniciar_servidor(self):
        from servidor_local import ServidorLocal
        try:
            self.servidor_local = ServidorLocal(self.puerto, self)
            self.host.setEnabled(False)
            self.mensaje.setText("Servidor local iniciado. Crea una sala y abre otra ventana para unirte.")
        except OSError:
            self.mensaje.setText("El puerto ya está ocupado. Si otra ventana inició el servidor, puedes crear una sala o unirte.")

    def _error_conexion(self, _error):
        if self.socket.state() == QAbstractSocket.SocketState.UnconnectedState:
            self._desconectado()
        self.mensaje.setText("No se pudo conectar. Inicia el servidor local e inténtalo de nuevo.")

    def conectar(self, tipo):
        if not self.nombre.text().strip():
            self.mensaje.setText("Escribe tu apodo.")
            return
        self.pendiente = {"version": 1, "tipo": tipo, "nombre": self.nombre.text().strip(), "codigo": self.codigo.text().strip().upper()}
        self.crear.setEnabled(False)
        self.unir.setEnabled(False)
        if self.socket.state() == QAbstractSocket.SocketState.ConnectedState:
            self._conectado()
        else:
            self.socket.open(QUrl(f"ws://127.0.0.1:{self.puerto}"))

    def _conectado(self):
        if self.pendiente:
            self.socket.sendTextMessage(json.dumps(self.pendiente))
            self.pendiente = None

    def _recibir(self, texto):
        try:
            dato = json.loads(texto)
            if dato['tipo'] in ('error', 'cerrada'):
                self.mensaje.setText(dato['mensaje'])
                self.vista.lbl_hud_consejo.setText(dato['mensaje'])
                if dato['tipo'] == 'cerrada':
                    self.socket.close()
                elif self.estado is None:
                    self.crear.setEnabled(True)
                    self.unir.setEnabled(True)
                return
            if dato['tipo'] != 'estado' or dato.get('version') != 1:
                raise ValueError("Versión desconocida")
            self.estado = dato
            self.salir.setEnabled(True)
            self.iniciar.setEnabled(dato['puede_iniciar'])
            self.iniciar.setText("Siguiente mano" if dato['partida'] else "Iniciar mano")
            self.crear.setEnabled(False)
            self.unir.setEnabled(False)
            self.sala.setText(f"Sala {dato['codigo']} · " + " / ".join(dato['nombres']))
            self.mensaje.setText("Prueba local conectada · La mesa sigue activa aunque cambies de pestaña.")
            if dato['partida']:
                self.lobby.hide()
                self.vista.show()
                self.sala_mesa.setText(f"Sala {dato['codigo']} · Amigos · Local")
                self.vista.mostrar(dato['partida'], dato['puede_iniciar'])
        except (ValueError, KeyError, TypeError):
            self.mensaje.setText("Respuesta de servidor incompatible.")
            self.vista.bloquear()

    def _enviar(self, tipo, **extra):
        if self.estado is None:
            return
        dato = {"version": 1, "tipo": tipo, "revision": self.estado['revision'], **extra}
        self.vista.bloquear()
        self.iniciar.setEnabled(False)
        self.socket.sendTextMessage(json.dumps(dato))

    def _actuar(self, accion, total):
        if self.estado and self.estado['partida']:
            self._enviar("accion", accion=accion, total=total, id_mano=self.estado['partida']['id_mano'])

    def _desconectado(self):
        self.estado = None
        self.pendiente = None
        self.vista.cancelar()
        self.vista.hide()
        self.lobby.show()
        self.sala.setText("Desconectado · Puedes crear otra sala")
        self.crear.setEnabled(True)
        self.unir.setEnabled(True)
        self.salir.setEnabled(False)
        self.iniciar.setEnabled(False)

    def cerrar(self):
        self.vista.cancelar()
        self.socket.close()
        if self.servidor_local:
            self.servidor_local.cerrar()

    def closeEvent(self, evento):
        self.cerrar()
        super().closeEvent(evento)
