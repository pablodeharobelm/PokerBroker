from PySide6.QtWidgets import QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, QPushButton, QDialog, QPlainTextEdit
import json
from constructor_tarjetas import crear_tarjeta_stat_global
from estadisticas import calcular_estadisticas
from persistencia import ErrorHistorial


def preparar_panel(panel):
    layout = panel.layout()
    if layout is None:
        layout = QVBoxLayout(panel)
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
    layout.setContentsMargins(20, 16, 20, 16)
    panel.setStyleSheet("background: #121212; color: #eeeeee;")
    return layout


def refrescar_interfaz_estadisticas(tab_stats, bd_local):
    layout = preparar_panel(tab_stats)
    try:
        datos = bd_local.cargar_historial()
    except ErrorHistorial as error:
        aviso = QLabel(str(error))
        aviso.setWordWrap(True)
        layout.addWidget(aviso)
        return
    stats = calcular_estadisticas(datos["manos"])
    titulo = QLabel("ESTADÍSTICAS DE TUS NUEVAS MANOS")
    titulo.setStyleSheet("font-size: 18px; font-weight: bold;")
    layout.addWidget(titulo)
    resumen = QLabel(f"{stats['manos']} manos completas · Balance de práctica: {stats['balance']:+,} fichas")
    resumen.setObjectName("resumen_estadisticas")
    layout.addWidget(resumen)
    antiguo = datos.get("historial_anterior")
    if antiguo is not None:
        aviso = QLabel(f"Conservamos {antiguo['manos_totales']:,} manos del historial anterior. Sus contadores no se mezclan con estas estadísticas porque no incluyen las acciones necesarias para recalcularlos.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #dfc17c;")
        layout.addWidget(aviso)
        boton = QPushButton("Consultar contadores anteriores")
        def mostrar_anteriores():
            dialogo = QDialog(tab_stats)
            dialogo.setWindowTitle("Historial anterior · contadores sin recalcular")
            dialogo.resize(540, 440)
            contenido = QVBoxLayout(dialogo)
            texto = QPlainTextEdit()
            texto.setReadOnly(True)
            texto.setPlainText(json.dumps(antiguo, indent=2, ensure_ascii=False))
            contenido.addWidget(texto)
            dialogo.exec()
        boton.clicked.connect(mostrar_anteriores)
        layout.addWidget(boton)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; }")
    contenedor = QWidget()
    grid = QGridLayout(contenedor)
    grid.setSpacing(12)
    for indice, (clave, metrica) in enumerate(stats["metricas"].items()):
        grid.addWidget(crear_tarjeta_stat_global(clave, metrica), indice // 4, indice % 4)
    scroll.setWidget(contenedor)
    layout.addWidget(scroll, 1)
    lectura = QLabel("Pulsa una métrica para ver su fórmula. Cada tarjeta muestra los casos y la base del cálculo. Sin oportunidades se muestra ‘Sin datos’. La muestra describe tu juego; no asigna una nota de habilidad.")
    lectura.setWordWrap(True)
    lectura.setStyleSheet("color: #aaaaaa;")
    layout.addWidget(lectura)
