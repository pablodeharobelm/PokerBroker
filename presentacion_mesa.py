"""Presentación común, alimentada por datos filtrados y sin motor de juego."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from logica_poker import Carta
import componentes_visuales as cv


POSICIONES_RIVALES = ((450, 70), (800, 120), (800, 300), (40, 300), (40, 120))


def convertir_carta(codigo):
    valor = {'A': 14, 'K': 13, 'Q': 12, 'J': 11}.get(codigo[:-1])
    return Carta(valor if valor is not None else int(codigo[:-1]), 'SHDC'.index(codigo[-1]))


def posiciones_relativas(cantidad, propio):
    """Índice visual -> asiento del servidor, preservando el orden horario."""
    visuales = {2: (0,), 3: (4, 1), 4: (3, 0, 2), 5: (3, 4, 1, 2), 6: (3, 4, 0, 1, 2)}[cantidad]
    return {visual: (propio + paso) % cantidad for paso, visual in enumerate(visuales, 1)}


class PresentacionMesa:
    def _cartas_visibles(self, layout, cartas, ancho, alto):
        cv.limpiar_layout(layout)
        for codigo in cartas:
            etiqueta = QLabel()
            ruta = cv.ruta_reverso() if codigo is None else cv.obtener_ruta_imagen_carta(convertir_carta(codigo))
            etiqueta.setPixmap(QPixmap(ruta).scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            etiqueta.setProperty('carta_visible', codigo or 'reverso')
            layout.addWidget(etiqueta)

    def _resaltar_asiento(self, panel, etiqueta, jugador, activo, propio, terminada):
        color = '#ffd700' if activo else '#555555'
        panel.setStyleSheet(f'background-color: rgba(30,30,30,230); border: 2px solid {color}; border-radius: 8px; padding: 5px;')
        estado = ('TU TURNO' if propio else 'SU TURNO') if activo else jugador['accion']
        if terminada:
            estado = 'Mano terminada'
        etiqueta.setText(f"{estado or 'Esperando'}\nEn esta calle: {0 if terminada else jugador['apuesta']:,}")
        etiqueta.setTextFormat(Qt.TextFormat.PlainText)
        etiqueta.setToolTip('Total de la calle, incluido en el bote.\nÚltima acción: ' + (jugador['accion'] or 'Ninguna'))
        etiqueta.setStyleSheet(f"color: {'#ffd700' if activo else '#dddddd'}; background-color: rgba(15,15,15,220); border: 1px solid {color}; border-radius: 4px; font: 11px 'Segoe UI';")
        etiqueta.setVisible(jugador['participando'])

    def pintar_estado(self, estado):
        propio = estado['tu_asiento']
        h = estado['jugadores'][propio]
        self.lbl_bote.setText(f"{estado['fase']} · BOTE: {estado['bote']:,}")
        self.fichas_bote.actualizar_bote(estado['bote'])
        self.lbl_nombre_propio.setText(f"[{h['posicion']}] {h['nombre']} (Tú)")
        self.lbl_nombre_propio.setToolTip(self.lbl_nombre_propio.text())
        self.lbl_fichas_propias.setText(f"{h['fichas']:,}")
        self._resaltar_asiento(self.panel_mio, self.lbl_apuesta_propia, h,
                              estado['turno'] == propio, True, estado['terminada'])
        self._cartas_visibles(self.layout_mano, h['cartas'], 75, 105)
        self._cartas_visibles(self.layout_centro, estado['mesa'], 65, 95)
        self.mapa_asientos = posiciones_relativas(len(estado['jugadores']), propio)
        for visual in range(5):
            perfil = self.asientos_visuales[visual]
            asiento = self.mapa_asientos.get(visual)
            if asiento is None:
                perfil['panel'].hide()
                self.lbl_apuestas_bots[visual].hide()
                for carta in perfil['cartas']:
                    carta.hide()
                continue
            j = estado['jugadores'][asiento]
            perfil['panel'].show()
            perfil['nombre'].setTextFormat(Qt.TextFormat.PlainText)
            perfil['nombre'].setText(f"[{j['posicion']}] {j['nombre']}")
            perfil['fichas'].setText(f"{j['fichas']:,}")
            activo = estado['turno'] == asiento
            color = '#666666' if j['retirado'] or not j['participando'] else '#ffd700' if activo else '#00ffcc'
            perfil['nombre'].setStyleSheet(f'color: {color}; border: none; background: transparent;')
            self._resaltar_asiento(perfil['panel'], self.lbl_apuestas_bots[visual], j, activo, False, estado['terminada'])
            for k, etiqueta in enumerate(perfil['cartas']):
                visible = j['participando'] and not j['retirado'] and k < len(j['cartas'])
                etiqueta.setVisible(visible)
                if visible:
                    codigo = j['cartas'][k]
                    ruta = cv.ruta_reverso() if codigo is None else cv.obtener_ruta_imagen_carta(convertir_carta(codigo))
                    etiqueta.setPixmap(QPixmap(ruta).scaled(40, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    etiqueta.setProperty('carta_visible', codigo or 'reverso')
