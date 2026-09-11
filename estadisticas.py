"""Estadísticas derivadas únicamente de manos completas con acciones registradas."""

from copy import deepcopy
from datetime import datetime, timezone


DEFINICIONES = {
    "VPIP": "Manos con una aportación voluntaria preflop / manos repartidas. Las ciegas obligatorias no cuentan como aportación voluntaria.",
    "PFR": "Manos con al menos una subida preflop / manos repartidas. Cada mano cuenta una sola vez.",
    "ATS": "Aperturas desde CO, BTN o SB con el bote sin entradas voluntarias / oportunidades legales de hacerlo. Una entrada previa pagando excluye el intento de robo.",
    "3-BET": "Resubidas preflop ante una única subida previa / oportunidades legales de resubir en esa situación. Incluye squeeze; excluye 4-bet y apuestas no reabiertas.",
    "WTSD": "Manos en las que llegaste al showdown / manos en las que viste el flop sin retirarte antes.",
    "WSD": "Showdowns donde recibiste parte de un bote / showdowns disputados. Incluye empates y botes secundarios, aunque el balance neto sea negativo; excluye devoluciones sin igualar.",
    "WWSF": "Manos donde recibiste parte de un bote después de ver el flop / manos donde viste el flop. Incluye victorias por retirada rival y empates.",
    "PF-FOLD": "Manos en las que te retiraste preflop / manos repartidas.",
    "FLOP-FOLD": "Folds ante una apuesta en el flop / decisiones frente a una apuesta en el flop. Una mano puede ofrecer varias decisiones.",
    "TURN-FOLD": "Folds ante una apuesta en el turn / decisiones frente a una apuesta en el turn. Los checks y los all-in sin decisión pendiente no son oportunidades.",
    "RIVER-FOLD": "Folds ante una apuesta en el river / decisiones frente a una apuesta en el river.",
}


def construir_registro(motor, heroe):
    if not motor.terminada:
        raise ValueError("Solo se pueden registrar manos terminadas.")
    def carta(c):
        return f"{c.valor}{c.palo}"
    return {
        "id": motor.id_mano, "inicio": motor.inicio_mano,
        "fin": datetime.now(timezone.utc).isoformat(), "heroe": heroe,
        "dealer": motor.dealer, "sb": motor.sb, "bb": motor.bb,
        "jugadores": [{"asiento": i, "nombre": j.nombre, "posicion": j.posicion,
                       "participando": j.participando, "perfil": j.perfil if i != heroe else None, "cartas": [carta(c) for c in j.cartas],
                       "fichas_iniciales": motor.fichas_iniciales[i], "fichas_finales": j.fichas,
                       "aportado": j.aportado, "retirado": j.retirado,
                       "premio": motor.pagos.get(i, 0), "devuelto": motor.devoluciones.get(i, 0)}
                      for i, j in enumerate(motor.jugadores)],
        "mesa": [carta(c) for c in motor.comunitarias],
        "ciegas": deepcopy(motor.ciegas_puestas), "acciones": deepcopy(motor.eventos),
        "showdown": motor.showdown, "vieron_flop": sorted(motor.vieron_flop),
        "botes": [{"cantidad": cantidad, "ganadores": list(ganadores)}
                  for cantidad, ganadores in motor.resultados],
    }


def calcular_estadisticas(manos):
    cuentas = {clave: [0, 0] for clave in DEFINICIONES}
    balance = 0
    total = 0
    for mano in manos:
        heroe = mano["heroe"]
        jugador = mano["jugadores"][heroe]
        if not jugador["participando"]:
            continue
        total += 1
        balance += jugador["fichas_finales"] - jugador["fichas_iniciales"]
        propias = [e for e in mano["acciones"] if e["jugador"] == heroe]
        preflop = [e for e in propias if e["fase"] == 0]
        cuentas["VPIP"][0] += any(e["cantidad"] > 0 for e in preflop)
        cuentas["PFR"][0] += any(e["accion"] == "raise" for e in preflop)
        cuentas["PF-FOLD"][0] += any(e["accion"] == "fold" for e in preflop)
        for clave in ("VPIP", "PFR", "PF-FOLD"):
            cuentas[clave][1] += 1
        limpio = True
        oportunidad_3bet = intento_3bet = False
        for e in mano["acciones"]:
            if e["fase"] != 0:
                break
            if e["jugador"] == heroe:
                if limpio and e["podia_subir"] and jugador["posicion"] in ("CO", "BTN", "SB", "BTN/SB"):
                    cuentas["ATS"][1] += 1
                    cuentas["ATS"][0] += e["accion"] == "raise"
                if e["subidas_previas"] == 1 and e["podia_subir"] and e["por_pagar"] > 0:
                    oportunidad_3bet = True
                    intento_3bet |= e["accion"] == "raise"
            if e["cantidad"] > 0:
                limpio = False
        cuentas["3-BET"][0] += intento_3bet
        cuentas["3-BET"][1] += oportunidad_3bet
        vio_flop = heroe in mano["vieron_flop"]
        showdown = mano["showdown"] and not jugador["retirado"]
        gano = jugador["premio"] > 0
        cuentas["WTSD"][0] += vio_flop and showdown
        cuentas["WTSD"][1] += vio_flop
        cuentas["WSD"][0] += showdown and gano
        cuentas["WSD"][1] += showdown
        cuentas["WWSF"][0] += vio_flop and gano
        cuentas["WWSF"][1] += vio_flop
        for fase, clave in enumerate(("FLOP-FOLD", "TURN-FOLD", "RIVER-FOLD"), 1):
            decisiones = [e for e in propias if e["fase"] == fase and e["por_pagar"] > 0]
            cuentas[clave][0] += sum(e["accion"] == "fold" for e in decisiones)
            cuentas[clave][1] += len(decisiones)
    return {"manos": total, "balance": balance, "metricas": {
        clave: {"casos": n, "oportunidades": d, "porcentaje": 100 * n / d if d else None}
        for clave, (n, d) in cuentas.items()}}
