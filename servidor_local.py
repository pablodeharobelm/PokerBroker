"""Servidor autoritativo WebSocket de pruebas, limitado a este ordenador."""
import json
import secrets
import sys
from PySide6.QtCore import QObject, QCoreApplication, QTimer
from PySide6.QtNetwork import QHostAddress
from PySide6.QtWebSockets import QWebSocketServer, QWebSocket
from motor_mesa import MotorMesa, JugadorMesa
from estado_mesa import vista_jugador
from shiboken6 import isValid


class ServidorLocal(QObject):
    def __init__(self, puerto=8765, parent=None, pausa_ms=850):
        super().__init__(parent)
        self.pausa_ms = pausa_ms
        self.salas, self.miembros = {}, {}
        self.servidor = QWebSocketServer("PokerBroker local", QWebSocketServer.SslMode.NonSecureMode, self)
        if not self.servidor.listen(QHostAddress.SpecialAddress.LocalHost, puerto):
            raise OSError(self.servidor.errorString())
        self.servidor.newConnection.connect(self._conectar)

    @property
    def puerto(self):
        return self.servidor.serverPort()

    def _conectar(self):
        socket = self.servidor.nextPendingConnection()
        socket.setParent(self)
        socket.setMaxAllowedIncomingMessageSize(4096)
        socket.textMessageReceived.connect(lambda texto: self._recibir(socket, texto))
        socket.disconnected.connect(lambda: self._salir(socket))

    def _enviar(self, socket, dato):
        socket.sendTextMessage(json.dumps(dato, ensure_ascii=False))

    def _recibir(self, socket, texto):
        try:
            if len(texto) > 4096:
                raise ValueError("Mensaje demasiado largo.")
            dato = json.loads(texto)
            if not isinstance(dato, dict) or type(dato.get("version")) is not int or dato["version"] != 1:
                raise ValueError("Protocolo incompatible.")
            tipo = dato.get("tipo")
            if tipo in ("crear", "unir"):
                if socket in self.miembros:
                    raise ValueError("Ya estás en una sala.")
                nombre = dato.get("nombre")
                if not isinstance(nombre, str) or not 1 <= len(nombre.strip()) <= 20 or any(ord(c) < 32 for c in nombre):
                    raise ValueError("Usa un apodo de 1 a 20 caracteres.")
                nombre = nombre.strip()
                if tipo == "crear":
                    codigo = secrets.token_hex(3).upper()
                    while codigo in self.salas:
                        codigo = secrets.token_hex(3).upper()
                    sala = {"clientes": [], "nombres": [], "motor": None, "revision": 0, "timer": None}
                    self.salas[codigo] = sala
                else:
                    codigo = dato.get("codigo")
                    if not isinstance(codigo, str) or codigo not in self.salas:
                        raise ValueError("Sala no encontrada.")
                    sala = self.salas[codigo]
                    if sala["motor"] or len(sala["clientes"]) >= 6:
                        raise ValueError("La sala está llena o ya empezó.")
                    if nombre.casefold() in [n.casefold() for n in sala["nombres"]]:
                        raise ValueError("Ese apodo ya está en uso.")
                self.miembros[socket] = (codigo, len(sala["clientes"]))
                sala["clientes"].append(socket)
                sala["nombres"].append(nombre)
            else:
                if socket not in self.miembros:
                    raise ValueError("Primero entra en una sala.")
                codigo, asiento = self.miembros[socket]
                sala = self.salas[codigo]
                if type(dato.get("revision")) is not int or dato["revision"] != sala["revision"]:
                    raise ValueError("La mesa ha cambiado; espera su actualización.")
                if tipo == "iniciar":
                    if asiento != 0 or len(sala["clientes"]) < 2:
                        raise ValueError("El creador inicia con al menos dos jugadores.")
                    if sala["motor"] is None:
                        sala["motor"] = MotorMesa([JugadorMesa(n, 2000) for n in sala["nombres"]])
                    sala["motor"].iniciar_mano()
                elif tipo == "accion":
                    m = sala["motor"]
                    if m is None or dato.get("id_mano") != m.id_mano:
                        raise ValueError("Mano incorrecta.")
                    if dato.get("accion") not in ("fold", "check", "call", "raise"):
                        raise ValueError("Acción inválida.")
                    m.actuar(asiento, dato["accion"], dato.get("total"))
                else:
                    raise ValueError("Mensaje desconocido.")
            sala["revision"] += 1
            self._difundir(codigo)
            self._programar(codigo)
        except (ValueError, TypeError, KeyError) as error:
            self._enviar(socket, {"tipo": "error", "mensaje": str(error)})
            if socket in self.miembros:
                self._difundir(self.miembros[socket][0])

    def _difundir(self, codigo):
        sala = self.salas[codigo]
        for i, socket in enumerate(sala["clientes"]):
            m = sala["motor"]
            dato = {"tipo": "estado", "version": 1, "codigo": codigo, "revision": sala["revision"],
                    "tu_asiento": i, "nombres": list(sala["nombres"]),
                    "puede_iniciar": i == 0 and len(sala["clientes"]) >= 2 and (m is None or
                        (m.terminada and sum(j.fichas > 0 for j in m.jugadores) >= 2)),
                    "partida": vista_jugador(m, i) if m else None}
            self._enviar(socket, dato)

    def _programar(self, codigo):
        sala = self.salas[codigo]
        m = sala["motor"]
        if sala["timer"] is not None:
            return
        if m is not None and not m.terminada and m.turno is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            sala["timer"] = timer
            timer.timeout.connect(lambda: self._avanzar(codigo))
            timer.start(self.pausa_ms)

    def _avanzar(self, codigo):
        sala = self.salas.get(codigo)
        if sala is None:
            return
        sala["timer"].deleteLater()
        sala["timer"] = None
        sala["motor"].avanzar_calle()
        sala["revision"] += 1
        self._difundir(codigo)
        self._programar(codigo)

    def _salir(self, socket):
        miembro = self.miembros.pop(socket, None)
        if miembro:
            sala = self.salas.pop(miembro[0], None)
            if sala:
                if sala["timer"]:
                    sala["timer"].stop()
                    sala["timer"].deleteLater()
                for otro in sala["clientes"]:
                    self.miembros.pop(otro, None)
                    if otro is not socket:
                        self._enviar(otro, {"tipo": "cerrada", "mensaje": "Un jugador salió. Crea otra sala para seguir probando."})
        if isValid(socket):
            socket.deleteLater()

    def cerrar(self):
        for sala in list(self.salas.values()):
            if sala["timer"]:
                sala["timer"].stop()
        self.salas.clear()
        self.miembros.clear()
        for socket in self.findChildren(QWebSocket):
            socket.disconnected.disconnect()
            socket.close()
            socket.deleteLater()
        self.servidor.close()


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    servidor = ServidorLocal()
    print(f"PokerBroker local: ws://127.0.0.1:{servidor.puerto}", flush=True)
    app.aboutToQuit.connect(servidor.cerrar)
    sys.exit(app.exec())
