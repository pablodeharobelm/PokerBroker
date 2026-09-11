from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, QRectF
import math


def distribuir_fichas(cantidad):
    """Escala visual progresiva, limitada a seis pilas de ocho fichas."""
    if cantidad <= 0:
        return []
    total = min(48, max(1, math.ceil(5 * math.log2(1 + cantidad / 20))))
    pilas = math.ceil(total / 8)
    base, resto = divmod(total, pilas)
    return [base + (i < resto) for i in range(pilas)]


class FichasBote(QWidget):
    """Pilas compactas a ambos lados del importe del bote, sin invadir las cartas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 65)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.cantidad = 0

    def actualizar_bote(self, cantidad):
        self.cantidad = max(0, cantidad)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        posiciones = (64, 304, 32, 336, 0, 368)
        colores = ("#c44043", "#3b81c4", "#369b71", "#8757b3", "#373c48", "#d3a741")
        for i, altura in enumerate(distribuir_fichas(self.cantidad)):
            x = posiciones[i] + 1
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 65))
            painter.drawEllipse(QRectF(x, 52, 30, 12))
            color = QColor(colores[i])
            for nivel in range(altura):
                y = 49 - nivel * 4
                painter.setPen(QPen(color.darker(175), 1))
                painter.setBrush(color.darker(125))
                painter.drawEllipse(QRectF(x, y + 3, 29, 12))
                painter.setBrush(color)
                painter.drawEllipse(QRectF(x, y, 29, 12))
                painter.setPen(QPen(QColor("#eadfcd"), 2))
                for inicio in (10, 100, 190, 280):
                    painter.drawArc(QRectF(x + 2, y + 1, 25, 9), inicio * 16, 24 * 16)
            painter.setPen(QPen(QColor("#e9dfcd"), 1))
            painter.setBrush(color.lighter(115))
            painter.drawEllipse(QRectF(x + 8, y + 3, 13, 6))

class MesaDibujo(QWidget):
    """Clase especializada para pintar el tapete verde ovalado oficial dentro de su propia pestaña."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo oscuro exterior de la mesa
        painter.fillRect(self.rect(), QColor(25, 25, 25))
        
        # Dibujar el óvalo del tapete verde central ajustado a las dimensiones internas
        borde_grosor = 15
        pen = QPen(QColor(40, 40, 40), borde_grosor)
        painter.setPen(pen)
        
        brush = QBrush(QColor(10, 100, 45)) # Verde casino
        painter.setBrush(brush)
        
        # Coordenadas y dimensiones adaptadas para que cuadre perfecto en el layout
        painter.drawEllipse(50, 40, 900, 430)
