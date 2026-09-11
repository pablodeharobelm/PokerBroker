"""Monte Carlo frente a manos uniformemente aleatorias, sin cartas ocultas reales."""

import math
import random
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from logica_poker import Carta
from evaluador_manos import EvaluadorManos


def estimar_equity(mano, mesa, rivales, muestras=600, semilla=None, cancelar=None):
    """Devuelve cuota media del bote (empates fraccionados) e incertidumbre muestral."""
    visibles = tuple(mano) + tuple(mesa)
    if len(mano) != 2 or len(mesa) not in (0, 3, 4, 5) or not 1 <= rivales <= 5 or muestras < 2:
        raise ValueError("Situación de equity inválida.")
    if len(set(visibles)) != len(visibles) or any(v not in range(2, 15) or p not in range(4) for v, p in visibles):
        raise ValueError("Cartas inválidas o duplicadas.")
    baraja = [Carta(v, p) for v in range(2, 15) for p in range(4) if (v, p) not in visibles]
    propias = [Carta(v, p) for v, p in mano]
    comunitarias = [Carta(v, p) for v, p in mesa]
    faltan = 5 - len(mesa)
    rng = random.Random(semilla)
    evaluador = EvaluadorManos()
    total = 0.0
    for _ in range(muestras):
        if cancelar is not None and cancelar.is_set():
            return None
        reparto = rng.sample(baraja, faltan + rivales * 2)
        board = comunitarias + reparto[:faltan]
        fuerza = evaluador.puntuar_mano(propias, board)
        puntos = [evaluador.puntuar_mano(reparto[faltan + i * 2:faltan + i * 2 + 2], board)
                  for i in range(rivales)]
        cuota = 0 if any(p > fuerza for p in puntos) else 1 / (1 + sum(p == fuerza for p in puntos))
        total += cuota
    media = total / muestras
    # Cota de Hoeffding para cuotas en [0, 1], con cobertura de al menos 95 %.
    # Evita un margen ficticiamente nulo cuando toda la muestra gana o empata.
    margen = math.sqrt(math.log(40) / (2 * muestras)) * 100
    return {"porcentaje": media * 100, "margen": margen,
            "muestras": muestras, "rivales": rivales}


class _Senales(QObject):
    resultado = Signal(object, object)


class _Trabajo(QRunnable):
    def __init__(self, clave, cancelar):
        super().__init__()
        self.clave, self.cancelar = clave, cancelar
        self.senales = _Senales()

    def run(self):
        try:
            _, mano, mesa, rivales = self.clave
            resultado = estimar_equity(mano, mesa, rivales, cancelar=self.cancelar)
        except Exception:
            resultado = {"error": "No se pudo calcular la equity."}
        self.senales.resultado.emit(self.clave, resultado)


class ServicioEquity(QObject):
    resultado = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clave = None
        self.cancelacion = Event()
        self.cache = {}

    def cancelar(self):
        self.cancelacion.set()
        self.clave = None

    def solicitar(self, clave):
        if clave == self.clave:
            return
        self.cancelar()
        self.clave = clave
        if clave in self.cache:
            self.resultado.emit(clave, self.cache[clave])
            return
        self.cancelacion = Event()
        trabajo = _Trabajo(clave, self.cancelacion)
        trabajo.senales.resultado.connect(self._recibir)
        QThreadPool.globalInstance().start(trabajo)

    @Slot(object, object)
    def _recibir(self, clave, resultado):
        if clave != self.clave or resultado is None:
            return
        if len(self.cache) > 24:
            self.cache.clear()
        self.cache[clave] = resultado
        self.resultado.emit(clave, resultado)
