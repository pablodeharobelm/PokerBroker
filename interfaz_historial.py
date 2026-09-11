"""Listado y detalle legible de las manos guardadas."""

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
                               QHeaderView, QPlainTextEdit, QSplitter)
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
    titulo = QLabel("HISTORIAL DE MANOS")
    titulo.setStyleSheet("font-size: 18px; font-weight: bold;")
    layout.addWidget(titulo)
    try:
        manos = list(reversed(bd_local.cargar_historial()["manos"]))
    except ErrorHistorial as error:
        aviso = QLabel(str(error))
        aviso.setWordWrap(True)
        layout.addWidget(aviso)
        return
    aviso = QLabel("Selecciona una mano para revisar sus acciones. Al terminar, el historial de práctica permite consultar las cartas de todos los participantes.")
    aviso.setWordWrap(True)
    layout.addWidget(aviso)
    if not manos:
        layout.addWidget(QLabel("Todavía no hay manos detalladas. Juega una mano completa para empezar."))
        layout.addStretch()
        return
    divisor = QSplitter(Qt.Orientation.Vertical)
    tabla = QTableWidget(len(manos), 5)
    tabla.setObjectName("tabla_historial")
    tabla.setHorizontalHeaderLabels(["Fecha", "Posición", "Tus cartas", "Mesa", "Balance"])
    tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    tabla.verticalHeader().hide()
    tabla.setStyleSheet("QTableWidget { background: #1c1c1c; color: #eeeeee; gridline-color: #333333; } QTableWidget::item:selected { background: #20584d; }")
    for fila, mano in enumerate(manos):
        h = mano["jugadores"][mano["heroe"]]
        valores = [fecha_local(mano["inicio"]), h["posicion"], " ".join(h["cartas"]),
                   " ".join(mano["mesa"]) or "Sin flop", f"{h['fichas_finales'] - h['fichas_iniciales']:+,}"]
        for columna, valor in enumerate(valores):
            tabla.setItem(fila, columna, QTableWidgetItem(valor))
    detalle = QPlainTextEdit()
    detalle.setObjectName("detalle_historial")
    detalle.setReadOnly(True)
    detalle.setStyleSheet("background: #191919; color: #dddddd; font-family: Consolas; font-size: 12px;")
    def seleccionar():
        fila = tabla.currentRow()
        if fila >= 0:
            detalle.setPlainText(detalle_mano(manos[fila]))
    tabla.itemSelectionChanged.connect(seleccionar)
    divisor.addWidget(tabla)
    divisor.addWidget(detalle)
    divisor.setSizes([200, 330])
    layout.addWidget(divisor, 1)
    tabla.selectRow(0)
