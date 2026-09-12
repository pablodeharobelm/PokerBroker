"""Mesa gráfica que solo utiliza la vista filtrada recibida por la red."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QFont
from PySide6.QtWidgets import QWidget
from componentes_visuales import DIRECTORIO_CARTAS, ruta_reverso
from componentes_dibujo import FichasBote


class MesaOnlineVisual(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado = None
        self.setMinimumSize(650, 330)
        self.fichas = FichasBote(self)
        self.fichas.setStyleSheet("background: transparent;")
        self.fichas.hide()
        self.imagenes = {}

    def mostrar(self, estado):
        self.estado = estado
        self.fichas.actualizar_bote(estado['bote'])
        self.update()

    def imagen_carta(self, codigo):
        if codigo not in self.imagenes:
            if codigo is None:
                ruta = ruta_reverso()
            else:
                valor = {'A': 'ace', 'K': 'king', 'Q': 'queen', 'J': 'jack'}.get(codigo[:-1], codigo[:-1])
                palo = {'S': 'spades', 'H': 'hearts', 'D': 'diamonds', 'C': 'clubs'}[codigo[-1]]
                ruta = str(Path(DIRECTORIO_CARTAS) / f'{valor}_of_{palo}.png')
            self.imagenes[codigo] = QPixmap(ruta)
        return self.imagenes[codigo]

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        escala = min(self.width() / 900, self.height() / 420)
        p.translate((self.width() - 900 * escala) / 2, (self.height() - 420 * escala) / 2)
        p.scale(escala, escala)
        p.setPen(QPen(QColor('#33382d'), 14))
        p.setBrush(QColor('#0b6335'))
        p.drawEllipse(QRectF(35, 32, 830, 350))
        p.setPen(QPen(QColor('#66835a'), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(52, 47, 796, 320))
        if not self.estado:
            return
        e = self.estado
        propios = e['tu_asiento']
        cantidad = len(e['jugadores'])
        # Orden horario, con el observador siempre abajo. Heads-up enfrente.
        plazas = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 5],
                  5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5]}[cantidad]
        posiciones = [(450, 365, 287), (110, 300, 228), (110, 83, 12),
                      (450, 12, 65), (790, 83, 12), (790, 300, 228)]
        for distancia in range(cantidad):
            i = (propios + distancia) % cantidad
            j = e['jugadores'][i]
            x, y, cartas_y = posiciones[plazas[distancia]]
            turno = e['turno'] == i and not e['terminada']
            p.setPen(QPen(QColor('#cfb477' if turno else '#526454'), 2))
            p.setBrush(QColor('#19271f'))
            p.drawRoundedRect(QRectF(x - 78, y, 156, 48), 8, 8)
            p.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
            p.setPen(QColor('#cfb477' if turno else '#efe6d2'))
            nombre = f"[{j['posicion']}] {j['nombre']}{' (Tú)' if i == propios else ''}"
            nombre = p.fontMetrics().elidedText(nombre, Qt.TextElideMode.ElideRight, 146)
            p.drawText(QRectF(x - 74, y + 3, 148, 20), Qt.AlignmentFlag.AlignCenter, nombre)
            p.setFont(QFont('Segoe UI', 10))
            p.drawText(QRectF(x - 75, y + 24, 150, 20), Qt.AlignmentFlag.AlignCenter, f"{j['fichas']:,}")
            # Los folds rivales se retiran de la mesa; tus cartas siguen visibles.
            if j['participando'] and (i == propios or not j['retirado']):
                for k, carta in enumerate(j['cartas']):
                    pix = self.imagen_carta(carta)
                    p.drawPixmap(QRectF(x - 49 + k * 51, cartas_y, 47, 66), pix, QRectF(pix.rect()))
            if i == propios:
                texto = 'Tu turno' if turno else j['accion']
                p.setPen(QColor('#cfb477'))
                p.drawText(QRectF(540, 330, 180, 42), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                           f"{texto}\nEn esta calle: {0 if e['terminada'] else j['apuesta']:,}")
            else:
                p.setPen(QColor('#e0d9bd'))
                # El asiento superior usa su lateral para no invadir el bote.
                rect = QRectF(x + 85, y + 5, 155, 42) if plazas[distancia] == 3 else QRectF(x - 78, y + 49, 156, 33)
                texto = 'Fold' if j['retirado'] else f"Aportado: {0 if e['terminada'] else j['apuesta']:,}"
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto)
        self.fichas.render(p, QPoint(250, 92))
        p.setPen(QPen(QColor('#cfb477'), 1))
        p.setBrush(QColor('#19271f'))
        p.drawRoundedRect(QRectF(352, 136, 196, 30), 10, 10)
        p.setPen(QColor('#cfb477'))
        p.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        p.drawText(QRectF(352, 136, 196, 30), Qt.AlignmentFlag.AlignCenter, f"{e['fase']} · Bote: {e['bote']:,}")
        for i, carta in enumerate(e['mesa']):
            pix = self.imagen_carta(carta)
            inicio = 450 - (len(e['mesa']) * 59 - 5) / 2
            p.drawPixmap(QRectF(inicio + i * 59, 183, 54, 76), pix, QRectF(pix.rect()))
