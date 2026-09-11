from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from ventana_ayuda import VentanaAyudaStats
from estadisticas import DEFINICIONES


def crear_tarjeta_stat_global(clave, metrica):
    tarjeta = QWidget()
    tarjeta.setObjectName("tarjeta_" + clave)
    tarjeta.setMinimumSize(200, 118)
    tarjeta.setStyleSheet("QWidget { background: #1a1a1a; border: 1px solid #303030; border-radius: 8px; } QLabel { border: none; background: transparent; color: #eeeeee; }")
    tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
    layout = QVBoxLayout(tarjeta)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)
    titulo = QLabel(clave)
    titulo.setStyleSheet("color: #bbbbbb; font-size: 12px; font-weight: bold;")
    porcentaje = metrica["porcentaje"]
    texto = "Sin datos" if porcentaje is None else f"{porcentaje:.1f} %"
    valor = QLabel(texto)
    valor.setObjectName("valor_" + clave)
    valor.setStyleSheet("color: #00ffcc; font-size: 23px; font-weight: bold;")
    detalle = QLabel(f"{metrica['casos']} / {metrica['oportunidades']} · casos / base")
    detalle.setStyleSheet("color: #aaaaaa; font-size: 11px;")
    barra = QProgressBar()
    barra.setRange(0, 1000)
    barra.setValue(round((porcentaje or 0) * 10))
    barra.setTextVisible(False)
    barra.setFixedHeight(5)
    barra.setStyleSheet("QProgressBar { background: #333333; border: none; } QProgressBar::chunk { background: #00bfa0; }")
    for widget in (titulo, valor, detalle, barra):
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(widget)
    tarjeta.setToolTip(DEFINICIONES[clave] + "\nPulsa para ver cómo se calcula.")
    def abrir(event):
        if event.button() == Qt.MouseButton.LeftButton:
            VentanaAyudaStats(clave, metrica, tarjeta).exec()
    tarjeta.mousePressEvent = abrir
    return tarjeta
