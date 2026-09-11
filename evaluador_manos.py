"""Evaluación de Texas Hold'em independiente de la interfaz."""

from collections import Counter
from itertools import combinations


class EvaluadorManos:
    CATEGORIAS = (
        "Carta Alta", "Pareja", "Dobles Parejas", "Tercia", "Escalera",
        "Color", "Full House", "Póker", "Escalera de Color",
    )
    NOMBRES = {11: "J", 12: "Q", 13: "K", 14: "A"}

    def _puntuar(self, cartas):
        valores = sorted((c.valor_num for c in cartas), reverse=True)
        grupos = sorted(((n, v) for v, n in Counter(valores).items()), reverse=True)
        color = len(cartas) == 5 and len({c.palo_num for c in cartas}) == 1
        unicos = sorted(set(valores))
        escalera = 0
        if len(unicos) == 5:
            if unicos[-1] - unicos[0] == 4:
                escalera = unicos[-1]
            elif unicos == [2, 3, 4, 5, 14]:
                escalera = 5
        if color and escalera:
            return (8, escalera)
        if grupos[0][0] == 4:
            return (7, grupos[0][1], *(v for v in valores if v != grupos[0][1]))
        if len(grupos) > 1 and grupos[0][0] == 3 and grupos[1][0] == 2:
            return (6, grupos[0][1], grupos[1][1])
        if color:
            return (5, *valores)
        if escalera:
            return (4, escalera)
        if grupos[0][0] == 3:
            return (3, grupos[0][1], *(v for v in valores if v != grupos[0][1]))
        parejas = sorted((v for n, v in grupos if n == 2), reverse=True)
        if len(parejas) == 2:
            return (2, *parejas, *(v for v in valores if v not in parejas))
        if parejas:
            return (1, parejas[0], *(v for v in valores if v != parejas[0]))
        return (0, *valores)

    def puntuar_mano(self, cartas_propias, cartas_comunitarias=()):
        """Tupla comparable: categoría y desempates de las cinco mejores cartas."""
        cartas = list(cartas_propias) + list(cartas_comunitarias)
        if not 1 <= len(cartas) <= 7:
            raise ValueError("La evaluación requiere entre una y siete cartas.")
        if len({(c.valor_num, c.palo_num) for c in cartas}) != len(cartas):
            raise ValueError("Una mano no puede contener cartas duplicadas.")
        return max(self._puntuar(c) for c in combinations(cartas, min(5, len(cartas))))

    def evaluar_mano(self, cartas_propias, cartas_comunitarias):
        """Describe la jugada principal sin enumerar las cartas de desempate."""
        puntos = self.puntuar_mano(cartas_propias, cartas_comunitarias)
        categoria = puntos[0]
        principal = self.NOMBRES.get(puntos[1], str(puntos[1]))
        if categoria == 0:
            return f"Carta alta: {principal}"
        if categoria in (1, 3, 7):
            nombre = {1: "Pareja", 3: "Trío", 7: "Póker"}[categoria]
            return f"{nombre} de {principal}"
        if categoria in (2, 6):
            secundaria = self.NOMBRES.get(puntos[2], str(puntos[2]))
            nombre = "Dobles parejas" if categoria == 2 else "Full house"
            return f"{nombre} de {principal} y {secundaria}"
        if categoria == 5:
            return f"Color al {principal}"
        nombre = "Escalera" if categoria == 4 else "Escalera de color"
        return f"{nombre} al {principal}"
