"""Dos clientes y un servidor real de loopback, sin tocar el historial local."""
import sys
from PySide6.QtWidgets import QApplication
from servidor_local import ServidorLocal
from interfaz_online import PanelOnline


def main():
    app = QApplication(sys.argv)
    servidor = ServidorLocal(0)
    ventanas = [PanelOnline(puerto=servidor.puerto) for _ in range(2)]
    for i, ventana in enumerate(ventanas):
        ventana.nombre.setText(f"Jugador {i + 1}")
        ventana.setWindowTitle(f"PokerBroker · Jugador {i + 1}")
        ventana.resize(1020, 706)
        ventana.host.setEnabled(False)
        ventana.show()
    def unir(_texto):
        estado = ventanas[0].estado
        if estado and ventanas[1].estado is None and ventanas[1].pendiente is None:
            ventanas[1].codigo.setText(estado['codigo'])
            ventanas[1].conectar('unir')
            ventanas[0].socket.textMessageReceived.disconnect(unir)
    ventanas[0].socket.textMessageReceived.connect(unir)
    ventanas[0].conectar('crear')
    app.aboutToQuit.connect(servidor.cerrar)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
