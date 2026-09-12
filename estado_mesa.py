"""Vista explícita por jugador: nunca serializa el motor ni la baraja."""


def vista_jugador(motor, asiento):
    if type(asiento) is not int or not 0 <= asiento < len(motor.jugadores):
        raise ValueError("Asiento inválido.")
    m = motor
    propio = m.jugadores[asiento]
    turno = not m.terminada and m.turno == asiento
    jugadores = []
    for i, j in enumerate(m.jugadores):
        visible = i == asiento or (m.terminada and m.showdown and not j.retirado and j.participando)
        jugadores.append({
            "asiento": i, "nombre": j.nombre, "fichas": j.fichas,
            "posicion": j.posicion, "apuesta": j.apuesta, "aportado": j.aportado,
            "retirado": j.retirado, "participando": j.participando, "accion": j.accion,
            "cartas": [c.valor + c.palo for c in j.cartas] if visible else [None] * len(j.cartas),
        })
    return {"id_mano": m.id_mano, "tu_asiento": asiento, "jugadores": jugadores,
            "mesa": [c.valor + c.palo for c in m.comunitarias], "fase": m.CALLES[m.fase],
            "bote": m.bote, "apuesta_actual": m.apuesta_actual, "turno": m.turno, "terminada": m.terminada,
            "pagos": [{"asiento": i, "cantidad": n} for i, n in m.pagos.items()],
            "devoluciones": [{"asiento": i, "cantidad": n} for i, n in m.devoluciones.items()],
            "controles": {"actuar": turno,
                          "pagar": min(m.por_pagar(asiento), propio.fichas) if turno else 0,
                          "subir": m.puede_subir(asiento) if turno else False,
                          "minimo": min(m.minimo_subida(), propio.apuesta + propio.fichas),
                          "maximo": propio.apuesta + propio.fichas}}
