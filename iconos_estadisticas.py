"""Símbolos vectoriales para las métricas, independientes de las fuentes emoji."""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QPolygonF


def icono_estadistica(clave):
    imagen = QPixmap(96, 96)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(2, 2)
    p.setPen(QPen(QColor("#cfb477"), 2.2, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)

    def flecha(x, y):
        p.drawLine(x, y + 17, x, y)
        p.drawPolyline(QPolygonF([QPointF(x - 5, y + 5), QPointF(x, y), QPointF(x + 5, y + 5)]))

    if clave == "VPIP":
        p.drawEllipse(QRectF(7, 9, 29, 29))
        p.drawEllipse(QRectF(13, 15, 17, 17))
        p.drawLine(32, 35, 43, 35)
        p.drawLine(38, 30, 38, 40)
    elif clave in ("PFR", "3-BET"):
        flecha(18, 10)
        if clave == "3-BET":
            flecha(31, 10)
        p.drawLine(9, 36, 38, 36)
    elif clave == "ATS":
        p.drawEllipse(QRectF(7, 20, 22, 17))
        p.drawArc(QRectF(7, 14, 22, 17), 0, 180 * 16)
        p.drawLine(23, 11, 41, 11)
        p.drawPolyline(QPolygonF([QPointF(35, 5), QPointF(41, 11), QPointF(35, 17)]))
    elif clave == "WTSD":
        p.drawRoundedRect(QRectF(5, 10, 18, 27), 3, 3)
        p.drawRoundedRect(QRectF(25, 10, 18, 27), 3, 3)
        p.drawEllipse(QRectF(11, 19, 6, 8))
        p.drawEllipse(QRectF(31, 19, 6, 8))
    elif clave in ("WSD", "WWSF"):
        p.drawArc(QRectF(13, 5, 22, 27), 180 * 16, 180 * 16)
        p.drawLine(13, 18, 13, 7)
        p.drawLine(35, 18, 35, 7)
        p.drawLine(13, 7, 35, 7)
        p.drawArc(QRectF(6, 9, 10, 15), 90 * 16, 180 * 16)
        p.drawArc(QRectF(32, 9, 10, 15), -90 * 16, 180 * 16)
        p.drawLine(24, 31, 24, 38)
        p.drawLine(17, 38, 31, 38)
        if clave == "WWSF":
            for x in (15, 24, 33):
                p.drawPoint(x, 44)
    else:
        p.drawRoundedRect(QRectF(11, 5, 26, 31), 4, 4)
        p.drawLine(7, 37, 40, 5)
        cantidad = {"PF-FOLD": 0, "FLOP-FOLD": 3, "TURN-FOLD": 4, "RIVER-FOLD": 5}[clave]
        for i in range(cantidad):
            p.drawPoint(24 - (cantidad - 1) * 3 + i * 6, 43)
    p.end()
    return imagen
