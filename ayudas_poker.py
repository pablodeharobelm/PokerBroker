"""Ayudas descriptivas: solo cartas visibles e importes públicos."""


def proyectos_visibles(mano, mesa):
    """Proyectos que se completan con una carta; no estima outs ganadores."""
    if len(mesa) not in (3, 4):
        return []
    cartas = list(mano) + list(mesa)
    proyectos = []
    nombres_palos = ("picas", "corazones", "diamantes", "tréboles")
    for palo in range(4):
        if sum(c.palo_num == palo for c in cartas) == 4:
            comun = all(c.palo_num != palo for c in mano)
            proyectos.append(f"Color ({nombres_palos[palo]})" + (" · en la mesa" if comun else ""))
    valores = {c.valor_num for c in cartas}
    if 14 in valores:
        valores.add(1)
    secuencias = [set(range(inicio, inicio + 5)) for inicio in range(1, 11)]
    # Una escalera ya formada no se presenta como proyecto.
    if not any(s <= valores for s in secuencias):
        faltantes = {next(iter(s - valores)) for s in secuencias if len(s - valores) == 1}
        faltantes = {14 if v == 1 else v for v in faltantes}
        if faltantes:
            abierta = any(set(range(inicio, inicio + 4)) <= valores for inicio in range(2, 11))
            tipo = "abierta" if abierta and len(faltantes) >= 2 else ("doble interna" if len(faltantes) >= 2 else "interna")
            nombres = {11: "J", 12: "Q", 13: "K", 14: "A"}
            valores_mesa = {c.valor_num for c in mesa}
            if 14 in valores_mesa:
                valores_mesa.add(1)
            comun = all(any(s <= (valores_mesa | {v, 1 if v == 14 else v}) for s in secuencias) for v in faltantes)
            rangos = "/".join(nombres.get(v, str(v)) for v in sorted(faltantes))
            proyectos.append(f"Escalera {tipo} ({rangos})" + (" · en la mesa" if comun else ""))
    return proyectos


def referencia_call(coste, aportaciones, heroe):
    """Umbral de retorno del call, limitado a las aportaciones disputables.

En botes secundarios solo sirve como referencia sobre la cuota esperada
del conjunto de botes elegibles, no como probabilidad de ganar una mano.
"""
    if coste <= 0:
        return {"coste": 0, "porcentaje": None, "bote_elegible": 0, "botes_limitados": False}
    limite = aportaciones[heroe] + coste
    exceso_propio = limite > max(v for i, v in enumerate(aportaciones) if i != heroe)
    bote = sum(min(v, limite) for v in aportaciones) + coste
    return {"coste": coste, "porcentaje": None if exceso_propio else 100 * coste / bote,
            "bote_elegible": bote, "botes_limitados": any(v > limite for v in aportaciones)}
