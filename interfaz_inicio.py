"""Entrada a los modos y herramientas de PokerBroker."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QToolButton
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon, QFont


def icono_menu(tipo):
    imagen = QPixmap(180, 100)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    if tipo in ("mesa", "online"):
        for x, y, simbolo, color in [(45, 8, "A", "#263d38"), (88, 18, "K", "#be655d")]:
            p.setBrush(QColor("#eceade" if tipo == "mesa" else "#8b9696"))
            p.drawRoundedRect(QRectF(x, y, 53, 76), 8, 8)
            p.setPen(QColor(color))
            p.setFont(QFont("Georgia", 27, QFont.Weight.Bold))
            p.drawText(QRectF(x, y, 53, 76), Qt.AlignmentFlag.AlignCenter, simbolo)
            p.setPen(Qt.PenStyle.NoPen)
    elif tipo == "stats":
        for i, alto in enumerate((25, 45, 37, 68)):
            p.setBrush(QColor("#cfb477"))
            p.drawRoundedRect(QRectF(40 + i * 27, 88 - alto, 17, alto), 5, 5)
    else:
        p.setPen(QPen(QColor("#d8c59a"), 4))
        p.drawRoundedRect(QRectF(49, 12, 82, 77), 10, 10)
        for y in (34, 51, 68):
            p.drawLine(66, y, 113, y)
    p.end()
    return QIcon(imagen)


def crear_inicio(navegar):
    panel = QWidget()
    panel.setStyleSheet("QWidget { background: #101512; color: #efe6d2; font-family: 'Segoe UI'; } QToolButton { background: #17392e; border: 1px solid #3b4d39; border-radius: 22px; padding: 18px; font-size: 19px; } QToolButton:hover { border-color: #cfb477; background: #244b3a; } QToolButton:pressed { background: #315b44; } QToolButton:disabled { color: #929888; background: #17251e; border-color: #22352f; }")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(64, 45, 64, 40)
    marca = QLabel("TU CLUB DE POKER")
    marca.setStyleSheet("color: #cfb477; font-size: 12px; font-weight: bold;")
    layout.addWidget(marca)
    titulo = QLabel("PokerBroker")
    titulo.setStyleSheet("font-size: 46px; font-weight: bold;")
    layout.addWidget(titulo)
    layout.addSpacing(28)
    grid = QGridLayout()
    grid.setSpacing(18)
    opciones = [("Jugar", "mesa"), ("Amigos · Prueba local", "online"),
                ("Estadísticas", "stats"), ("Historial", "historial")]
    for i, (texto, destino) in enumerate(opciones):
        boton = QToolButton()
        boton.setText(texto)
        boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        boton.setIcon(icono_menu(destino or "online"))
        boton.setIconSize(QSize(180, 100))
        boton.setMinimumSize(410, 175)
        boton.setAccessibleName("Jugar contra bots" if destino == "mesa" else texto)
        boton.setToolTip("Continuar la mesa contra bots" if destino == "mesa" else texto)
        boton.setEnabled(destino is not None)
        if destino:
            boton.clicked.connect(lambda checked=False, d=destino: navegar(d))
        grid.addWidget(boton, i // 2, i % 2)
    layout.addLayout(grid)
    layout.addStretch()
    nota = QLabel("PRÁCTICA LOCAL")
    nota.setStyleSheet("color: #929888; font-size: 12px;")
    layout.addWidget(nota)
    return panel
