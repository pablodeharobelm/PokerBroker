"""Tramos de lectura orientativos, no objetivos de rentabilidad.

Los cortes son convenciones educativas de la aplicación. VPIP/PFR, 3-bet
y WTSD se apoyan en perfiles habituales; los demás son tramos descriptivos.
No aplicar rangos de fold-to-cbet a nuestros folds frente a cualquier apuesta.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import QRectF, Qt

RANGOS = {
    "VPIP": (20, 30, ("Entras en pocas manos", "Participación moderada", "Entras muy a menudo")),
    "PFR": (15, 25, ("Subes pocas manos", "Subidas moderadas", "Subes muy a menudo")),
    "ATS": (25, 45, ("Pocos intentos de robo", "Robos moderados", "Robos frecuentes")),
    "3-BET": (4, 9, ("Resubes poco", "Resubidas moderadas", "Resubes a menudo")),
    "WTSD": (22, 30, ("Pocos showdowns", "Showdowns moderados", "Llegas mucho al final")),
    "WSD": (45, 60, ("Cobras pocos showdowns", "Cobros intermedios", "Cobras muchos showdowns")),
    "WWSF": (35, 50, ("Cobras pocos botes", "Cobros intermedios", "Cobras muchos botes")),
    "PF-FOLD": (60, 80, ("Te retiras poco", "Retiradas intermedias", "Te retiras muy a menudo")),
    "FLOP-FOLD": (30, 60, ("Abandonas poco", "Abandonos intermedios", "Abandonas a menudo")),
    "TURN-FOLD": (30, 60, ("Abandonas poco", "Abandonos intermedios", "Abandonas a menudo")),
    "RIVER-FOLD": (30, 60, ("Abandonas poco", "Abandonos intermedios", "Abandonas a menudo")),
}


def interpretar(clave, porcentaje):
    bajo, alto, textos = RANGOS[clave]
    if porcentaje is None:
        return "Sin oportunidades"
    return textos[0 if porcentaje < bajo else 1 if porcentaje <= alto else 2]


def explicacion_rangos(clave):
    bajo, alto, textos = RANGOS[clave]
    texto = (f"Menos de {bajo}%: {textos[0]}.\n{bajo}–{alto}%: {textos[1]}.\n"
             f"Más de {alto}%: {textos[2]}.\n\n"
             "Son tramos orientativos de frecuencia, no una escala de bueno a malo. "
             "Los cortes son una guía educativa, no límites óptimos validados. "
             "Importan la posición, los rivales, los jugadores activos y las fichas efectivas. "
             "Con menos de 100 oportunidades mostramos «Poca muestra»; superarlas no garantiza fiabilidad.")
    if clave in ("WSD", "WWSF"):
        texto += " Cobrar incluye empates y botes secundarios: un porcentaje alto no implica beneficio neto."
    elif clave.endswith("FOLD"):
        texto += " Retirarte mucho puede ceder botes; hacerlo poco puede llevarte a pagar de más. Revisa las manos y tamaños de apuesta. Estos datos no son fold-to-cbet."
    elif clave in ("VPIP", "PFR", "3-BET", "ATS"):
        texto += " Un 100% significa hacerlo en todas las oportunidades, no jugar perfectamente. Revisa si estás entrando o subiendo con demasiadas manos."
    elif clave == "WTSD":
        texto += " Llegar siempre al showdown puede indicar que pagas demasiado; interprétalo junto con WSD y las manos concretas."
    return texto


class BarraRangos(QWidget):
    def __init__(self, clave, porcentaje):
        super().__init__()
        self.clave, self.porcentaje = clave, porcentaje
        self.setFixedHeight(30)
        self.setAccessibleName("Rangos de " + clave)
        self.setToolTip(explicacion_rangos(clave))

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ancho = self.width() - 10
        bajo, alto, _ = RANGOS[self.clave]
        p.setPen(Qt.PenStyle.NoPen)
        for inicio, fin, color in [(0, bajo, "#687e89"), (bajo, alto, "#b7a573"), (alto, 100, "#94715c")]:
            p.setBrush(QColor(color))
            p.drawRect(QRectF(5 + ancho * inicio / 100, 5, ancho * (fin - inicio) / 100, 8))
        if self.porcentaje is not None:
            x = 5 + ancho * max(0, min(100, self.porcentaje)) / 100
            p.setPen(QPen(QColor("#fff4d8"), 3))
            p.drawLine(int(x), 1, int(x), 17)
        p.setPen(QColor("#bcbdb2"))
        fuente = p.font()
        fuente.setPixelSize(9)
        p.setFont(fuente)
        p.drawText(QRectF(5, 17, 30, 13), Qt.AlignmentFlag.AlignLeft, "0%")
        p.drawText(QRectF(self.width() - 35, 17, 30, 13), Qt.AlignmentFlag.AlignRight, "100%")
