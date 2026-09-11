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
    layout.setContentsMargins(32, 24, 32, 24)
    layout.setSpacing(16)
    panel.setStyleSheet("QWidget { background: #101512; color: #efe6d2; font-family: 'Segoe UI'; } QPushButton { background: #244333; border: 1px solid #465139; border-radius: 6px; padding: 10px; } QPushButton:hover { background: #2d4853; }")
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
    titulo = QLabel("Estadísticas")
    titulo.setStyleSheet("font-size: 30px; font-weight: bold;")
    layout.addWidget(titulo)
    resumen = QLabel(f"{stats['manos']:,} {'mano' if stats['manos'] == 1 else 'manos'}     /     {stats['balance']:+,} fichas")
    resumen.setObjectName("resumen_estadisticas")
    resumen.setStyleSheet("background: #17392e; border: 1px solid #465139; border-radius: 10px; padding: 20px; color: #cfb477; font-size: 18px;")
    layout.addWidget(resumen)
    antiguo = datos.get("historial_anterior")
    if antiguo is not None:
        boton = QPushButton("Archivo anterior")
        boton.setToolTip(f"{antiguo['manos_totales']:,} manos antiguas conservadas, excluidas de estas métricas porque no incluyen las acciones necesarias.")
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
    lectura = QLabel("Tramos orientativos, no notas: más alto no siempre es mejor. Pulsa para interpretar cada métrica.")
    lectura.setWordWrap(True)
    lectura.setStyleSheet("color: #aaaaaa;")
    layout.addWidget(lectura)
