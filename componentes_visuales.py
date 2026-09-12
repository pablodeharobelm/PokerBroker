import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt

DIRECTORIO_CARTAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cartas")


def ruta_reverso():
    return os.path.join(DIRECTORIO_CARTAS, "back.png")


def obtener_ruta_imagen_carta(carta):
    valores = {"A": "ace", "K": "king", "Q": "queen", "J": "jack"}
    palos = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}
    valor = valores.get(carta.valor, carta.valor)
    return os.path.join(DIRECTORIO_CARTAS, f"{valor}_of_{palos[carta.palo]}.png")


def crear_cuadro_perfil(parent, nombre, fichas, x, y):
    """Genera un widget estético oscuro para los asientos de la mesa con cartas ocultas incorporadas."""
    # Dos cartas encima del perfil, sin cubrir su nombre.
    ruta_back = ruta_reverso()

    pixmap_back = QPixmap(ruta_back)

    cartas_visuales = []
    if "Tú" not in nombre:
        for i in range(2):
            lbl_carta_oculta = QLabel(parent)
            cartas_visuales.append(lbl_carta_oculta)
            if not pixmap_back.isNull():
                pix_escalado = pixmap_back.scaled(40, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl_carta_oculta.setPixmap(pix_escalado)
            else:
                lbl_carta_oculta.setStyleSheet("background-color: #772222; border-radius: 3px;")

            lbl_carta_oculta.setFixedSize(40, 58)

            lbl_carta_oculta.move(x + 28 + (i * 44), y - 62)
            lbl_carta_oculta.show()

    # 2. CUADRO OSCURO DEL PERFIL
    estilo_perfil = "background-color: rgba(30, 30, 30, 230); color: white; border: 2px solid #555555; border-radius: 8px; padding: 5px;"
    panel = QWidget(parent)
    panel.setStyleSheet(estilo_perfil)
    panel.setFixedSize(140, 55)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setSpacing(2)

    lbl_nombre = QLabel(nombre)
    lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_nombre.setFont(QFont("Arial", 9, QFont.Weight.Bold))
    lbl_nombre.setStyleSheet("color: #E0E0E0; border: none; background: transparent;")

    lbl_fichas = QLabel(fichas)
    lbl_fichas.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_fichas.setFont(QFont("Arial", 10))
    lbl_fichas.setStyleSheet("color: #A0A0A0; border: none; background: transparent;")

    layout.addWidget(lbl_nombre)
    layout.addWidget(lbl_fichas)
    panel.move(x, y)

    return {"panel": panel, "nombre": lbl_nombre, "fichas": lbl_fichas, "cartas": cartas_visuales}

def limpiar_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
