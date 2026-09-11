from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from ventana_ayuda import VentanaAyudaStats
from estadisticas import DEFINICIONES
from iconos_estadisticas import icono_estadistica
from rangos_estadisticas import BarraRangos, RANGOS, interpretar, explicacion_rangos


def crear_tarjeta_stat_global(clave, metrica):
    tarjeta = QWidget()
    tarjeta.setObjectName("tarjeta_" + clave)
    tarjeta.setMinimumSize(200, 182)
    tarjeta.setStyleSheet("QWidget { background: #17392e; border: 1px solid #465139; border-radius: 12px; } QWidget:hover { border-color: #cfb477; } QLabel { border: none; background: transparent; color: #eeeeee; }")
    tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
    layout = QVBoxLayout(tarjeta)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)
    titulo = QLabel(clave)
    titulo.setStyleSheet("color: #bbbbbb; font-size: 12px; font-weight: bold;")
    cabecera = QWidget()
    cabecera.setFixedHeight(38)
    cabecera.setStyleSheet("border: none; background: transparent;")
    fila = QHBoxLayout(cabecera)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(10)
    dibujo = QLabel()
    dibujo.setFixedSize(38, 38)
    dibujo.setPixmap(icono_estadistica(clave).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    fila.addWidget(dibujo)
    fila.addWidget(titulo, 1)
    porcentaje = metrica["porcentaje"]
    texto = "Sin datos" if porcentaje is None else f"{porcentaje:.1f} %"
    valor = QLabel(texto)
    valor.setObjectName("valor_" + clave)
    valor.setStyleSheet("color: #efe6d2; font-size: 23px; font-weight: bold;")
    barra = BarraRangos(clave, porcentaje)
    bajo, alto, _ = RANGOS[clave]
    lectura = QLabel(interpretar(clave, porcentaje))
    lectura.setStyleSheet("font-size: 11px; color: #efe6d2;")
    referencia = QLabel(f"Tramo medio: {bajo}–{alto}%")
    referencia.setStyleSheet("font-size: 10px; color: #bcbdb2;")
    n = metrica['oportunidades']
    muestra = QLabel(f"{'Poca muestra' if n < 100 else 'Oportunidades'} · {n}")
    muestra.setStyleSheet("font-size: 10px; color: #cfb477;")
    for widget in (cabecera, valor, barra, referencia, lectura, muestra):
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(widget)
    tarjeta.setToolTip(DEFINICIONES[clave] + f"\n{metrica['casos']} casos / {metrica['oportunidades']} oportunidades.\n" + explicacion_rangos(clave))
    def abrir(event):
        if event.button() == Qt.MouseButton.LeftButton:
            VentanaAyudaStats(clave, metrica, tarjeta).exec()
    tarjeta.mousePressEvent = abrir
    return tarjeta
