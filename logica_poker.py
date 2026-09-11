import random
import os
import json

class Carta:
    """Clase Carta pura basada en IDs numéricos internos compatible con componentes_visuales."""
    def __init__(self, valor_num, palo_num):
        self.valor_num = valor_num  # 2 al 14 (Donde 11=J, 12=Q, 13=K, 14=A)
        self.palo_num = palo_num    # 0=Espadas(S), 1=Corazones(H), 2=Diamantes(D), 3=Tréboles(C)

        # Mapeos inversos para comunicación con la interfaz gráfica
        mapeo_valores = {2:"2", 3:"3", 4:"4", 5:"5", 6:"6", 7:"7", 8:"8", 9:"9", 10:"10", 11:"J", 12:"Q", 13:"K", 14:"A"}
        # CORREGIDO: Iniciales en mayúsculas estrictas para encajar con componentes_visuales.py y evitar el KeyError
        mapeo_palos = {0:"S", 1:"H", 2:"D", 3:"C"}

        self.valor = mapeo_valores[valor_num]
        self.rango = self.valor
        self.palo = mapeo_palos[palo_num]


class Baraja:
    """Genera, baraja y reparte cartas reales sin duplicados."""
    def __init__(self, rng=None):
        self.cartas = [Carta(v, p) for v in range(2, 15) for p in range(4)]
        (rng or random).shuffle(self.cartas)

    def repartir(self, cantidad):
        if type(cantidad) is not int or not 0 <= cantidad <= len(self.cartas):
            raise ValueError("Cantidad de cartas no disponible en la baraja.")
        mano = self.cartas[:cantidad]
        del self.cartas[:cantidad]
        return mano

from evaluador_manos import EvaluadorManos

class GestorPosiciones:
    """Maneja la rotación circular legal de la mesa según las agujas del reloj."""
    def __init__(self):
        self.posiciones_base = ["BTN", "SB", "BB", "UTG", "MP", "CO"]

    def obtener_posiciones_ronda(self, indice_dealer):
        # Rotamos el array de forma circular perfecta usando el Dealer asignado
        resultado = []
        for i in range(6):
            idx = (i - indice_dealer) % 6
            resultado.append(self.posiciones_base[idx])
        return resultado

class TrackerEstadisticasBots:
    """HUD estático para los perfiles de los oponentes de la mesa."""
    def simular_mano_y_calcular_hud(self, nombre_bot):
        # Muestra una simulación de HUD estándar profesional para dar ambiente de software real
        return "VPIP: 24% | PFR: 19% | 3B: 6%\nAF: 2.5 | Hands: 1.2k"

class Usuario:
    def __init__(self, nombre, banco_inicial=10000):
        self.nombre = nombre
        self.banco = banco_inicial
    def iniciar_sesion_mesa(self, fichas):
        return SesionMesa(fichas)

class SesionMesa:
    def __init__(self, fichas):
        self.fichas_actuales = fichas

from persistencia import BaseDatosLocal

class CalculadorEquity:
    """Compatibilidad con el calculador Monte Carlo de manos aleatorias."""
    def simular_equity_montecarlo(self, mano, mesa, rivales=1, muestras=600):
        from equity import estimar_equity
        convertir = lambda cartas: tuple((c.valor_num, c.palo_num) for c in cartas)
        return estimar_equity(convertir(mano), convertir(mesa), rivales, muestras)["porcentaje"]
