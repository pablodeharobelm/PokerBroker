"""Listado y detalle legible de las manos guardadas."""

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
                               QHeaderView, QPlainTextEdit, QSplitter, QWidget,
                               QVBoxLayout, QHBoxLayout, QPushButton)
from PySide6.QtGui import QColor
from interfaz_estadisticas import preparar_panel
from persistencia import ErrorHistorial


def fecha_local(fecha):
    return datetime.fromisoformat(fecha).astimezone().strftime("%d/%m/%Y %H:%M:%S")


def detalle_mano(mano):
    jugadores = mano["jugadores"]
    heroe = jugadores[mano["heroe"]]
    lineas = [f"Mano {mano['id']}", f"Inicio: {fecha_local(mano['inicio'])} · Ciegas: {mano['sb']}/{mano['bb']}",
              f"Tú: {heroe['nombre']} · {heroe['posicion']} · {' '.join(heroe['cartas'])}",
              "S = picas · H = corazones · D = diamantes · C = tréboles", "", "JUGADORES"]
    for j in jugadores:
        if j["participando"]:
            lineas.append(f"[{j['posicion']}] {j['nombre']}: {j['fichas_iniciales']:,} → {j['fichas_finales']:,} fichas · Cartas: {' '.join(j['cartas'])}" + (" · Fold" if j["retirado"] else ""))
            if j.get("perfil"):
                lineas.append(f"  Estilo del rival: {j['perfil']}")
    lineas.extend(["", "CIEGAS"])
    for ciega in mano["ciegas"]:
        lineas.append(f"{jugadores[ciega['jugador']]['nombre']} · {ciega['tipo']}: {ciega['cantidad']}")
    for fase, calle in enumerate(("PREFLOP", "FLOP", "TURN", "RIVER")):
        cantidad_mesa = (0, 3, 4, 5)[fase]
        if fase and len(mano["mesa"]) < cantidad_mesa:
            break
        lineas.extend(["", calle + (" · Mesa: " + " ".join(mano["mesa"][:cantidad_mesa]) if fase else "")])
        for e in mano["acciones"]:
            if e["fase"] != fase:
                continue
            accion = {"fold": "Fold", "check": "Check", "call": f"Call {e['cantidad']}",
                      "raise": f"Apuesta/subida a {e['total_calle']} (añade {e['cantidad']})"}[e["accion"]]
            lineas.append(f"{jugadores[e['jugador']]['nombre']}: {accion}" + (" · All-in" if e["all_in"] else "") + f" · Bote: {e['bote_despues']}")
    lineas.extend(["", "RESULTADO · " + ("Showdown" if mano["showdown"] else "Retirada de los rivales")])
    for i, bote in enumerate(mano["botes"], 1):
        nombres = ", ".join(jugadores[j]["nombre"] for j in bote["ganadores"])
        lineas.append(f"Bote {i}: {bote['cantidad']:,} fichas → {nombres}")
    for j in jugadores:
        if j["devuelto"]:
            lineas.append(f"Sin igualar: se devuelven {j['devuelto']:,} a {j['nombre']}")
    lineas.append(f"Tu balance neto: {heroe['fichas_finales'] - heroe['fichas_iniciales']:+,} fichas")
    return "\n".join(lineas)


def refrescar_historial(panel, bd_local):
    layout = preparar_panel(panel)
    titulo = QLabel("Historial")
    titulo.setStyleSheet("font-size: 30px; font-weight: bold;")
    layout.addWidget(titulo)
    try:
        manos = list(reversed(bd_local.cargar_historial()["manos"]))
    except ErrorHistorial as error:
        aviso = QLabel(str(error))
        aviso.setWordWrap(True)
        layout.addWidget(aviso)
        return
    if not manos:
        vacio = QLabel("Tu primera mano te espera")
        vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vacio.setStyleSheet("font-size: 24px; color: #7fa399; padding: 120px 0;")
        layout.addWidget(vacio)
        layout.addStretch()
        return
    divisor = QSplitter(Qt.Orientation.Horizontal)
    tabla = QTableWidget(len(manos), 3)
    tabla.setObjectName("tabla_historial")
    tabla.setHorizontalHeaderLabels(["Fecha", "Mano", "Balance"])
    tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    tabla.verticalHeader().hide()
    tabla.verticalHeader().setDefaultSectionSize(56)
    tabla.setShowGrid(False)
    tabla.setAlternatingRowColors(True)
    tabla.setStyleSheet("QTableWidget { background: #142a22; alternate-background-color: #17392e; color: #efe6d2; border: 1px solid #465139; font-size: 12px; } QTableWidget::item:selected { background: #36553b; color: white; } QHeaderView::section { background: #244333; color: #d3c39e; border: none; padding: 12px; }")
    for fila, mano in enumerate(manos):
        h = mano["jugadores"][mano["heroe"]]
        simbolos = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
        balance = h['fichas_finales'] - h['fichas_iniciales']
        valores = [datetime.fromisoformat(mano['inicio']).astimezone().strftime('%d/%m %H:%M'),
                   " ".join(c[:-1] + simbolos[c[-1]] for c in h['cartas']), f"{balance:+,}"]
        for columna, valor in enumerate(valores):
            item = QTableWidgetItem(valor)
            item.setToolTip(fecha_local(mano['inicio']) if columna == 0 else valor)
            if columna == 2:
                item.setForeground(QColor("#7dddb5" if balance >= 0 else "#ed9990"))
            tabla.setItem(fila, columna, item)
    visual = QWidget()
    visual.setMinimumWidth(430)
    contenido = QVBoxLayout(visual)
    contenido.setContentsMargins(24, 12, 12, 12)
    contenido.setSpacing(14)
    resultado = QLabel()
    resultado.setObjectName("balance_mano_visual")
    contenido.addWidget(resultado)
    posicion = QLabel()
    contenido.addWidget(posicion)
    contenido.addWidget(QLabel("TU MANO"))
    propias = QWidget()
    fila_propias = QHBoxLayout(propias)
    fila_propias.setContentsMargins(0, 0, 0, 0)
    contenido.addWidget(propias)
    contenido.addWidget(QLabel("MESA"))
    board = QWidget()
    fila_board = QHBoxLayout(board)
    fila_board.setContentsMargins(0, 0, 0, 0)
    contenido.addWidget(board)
    def pintar_cartas(fila, cartas, huecos):
        while fila.count():
            item = fila.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for i in range(huecos):
            c = cartas[i] if i < len(cartas) else None
            etiqueta = QLabel()
            etiqueta.setFixedSize(58, 82)
            etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if c:
                simbolo = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}[c[-1]]
                etiqueta.setText(c[:-1] + "\n" + simbolo)
                color = "#bf5c55" if c[-1] in "HD" else "#223b34"
                etiqueta.setStyleSheet(f"background: #f0ede2; color: {color}; border-radius: 9px; font: bold 22px 'Segoe UI';")
            else:
                etiqueta.setStyleSheet("background: #1b2b2a; border: 1px dashed #3a534b; border-radius: 9px;")
            fila.addWidget(etiqueta)
        fila.addStretch()
    boton_detalle = QPushButton("Ver acciones")
    boton_detalle.setCheckable(True)
    boton_detalle.setObjectName("alternar_detalle_historial")
    contenido.addWidget(boton_detalle)
    detalle = QPlainTextEdit()
    detalle.setObjectName("detalle_historial")
    detalle.setReadOnly(True)
    detalle.setMaximumHeight(190)
    detalle.setStyleSheet("background: #142a22; color: #d5e2e9; border: 1px solid #465139; border-radius: 8px; padding: 14px; font-family: Consolas; font-size: 12px;")
    contenido.addWidget(detalle)
    detalle.hide()
    contenido.addStretch()
    def alternar(visible):
        detalle.setVisible(visible)
        boton_detalle.setText("Ocultar acciones" if visible else "Ver acciones")
    boton_detalle.toggled.connect(alternar)
    def seleccionar():
        fila = tabla.currentRow()
        if fila >= 0:
            detalle.setPlainText(detalle_mano(manos[fila]))
            mano = manos[fila]
            h = mano['jugadores'][mano['heroe']]
            neto = h['fichas_finales'] - h['fichas_iniciales']
            resultado.setText(f"{neto:+,} fichas")
            resultado.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {'#7dddb5' if neto >= 0 else '#ed9990'};")
            posicion.setText(h['posicion'] + " · " + ("Showdown" if mano['showdown'] else "Sin showdown"))
            pintar_cartas(fila_propias, h['cartas'], 2)
            pintar_cartas(fila_board, mano['mesa'], 5)
    tabla.itemSelectionChanged.connect(seleccionar)
    divisor.addWidget(tabla)
    divisor.addWidget(visual)
    divisor.setSizes([450, 490])
    layout.addWidget(divisor, 1)
    tabla.selectRow(0)
