"""Rivales de práctica con reglas heurísticas, sin acceso al motor ni a la baraja.

Las puntuaciones internas ordenan situaciones; no son porcentajes de equity.
"""

from dataclasses import dataclass
from evaluador_manos import EvaluadorManos
from ayudas_poker import proyectos_visibles


@dataclass(frozen=True)
class PerfilBot:
    nombre: str
    descripcion: str
    entrada: float
    agresividad: float
    farol: float
    tamano: float


PERFILES = {
    "conservador": PerfilBot("Conservador", "Selecciona más sus manos y evita pagar caro con manos débiles.", .62, .30, .02, .50),
    "equilibrado": PerfilBot("Equilibrado", "Combina apuestas por valor, checks y algunos faroles.", .52, .53, .06, .60),
    "agresivo": PerfilBot("Agresivo", "Abre más manos y apuesta o resube con mayor frecuencia.", .44, .78, .14, .75),
    "pagador": PerfilBot("Pagador", "Entra en más botes y prefiere pagar a resubir.", .38, .16, .01, .45),
}


@dataclass(frozen=True)
class SituacionBot:
    mano: tuple
    mesa: tuple
    posicion: str
    fase: int
    fichas: int
    apuesta_propia: int
    apuesta_actual: int
    coste: int
    bote_disputable: int  # Incluye el call limitado al stack.
    bb: int
    minimo_subida: int
    puede_subir: bool
    rivales: int
    subidas_preflop: int
    subidas_calle: int
    limpers: int
    ultimo_en_hablar: bool


def fuerza_preflop(mano):
    alto, bajo = sorted((c.valor_num for c in mano), reverse=True)
    if alto == bajo:
        return .50 + alto / 28
    fuerza = .25 + alto * .02 + bajo * .015
    fuerza += .05 if mano[0].palo_num == mano[1].palo_num else 0
    fuerza -= min(.18, max(0, alto - bajo - 1) * .03)
    return min(.95, fuerza)


def fuerza_postflop(mano, mesa):
    evaluador = EvaluadorManos()
    puntos = evaluador.puntuar_mano(mano, mesa)
    categoria = puntos[0]
    fuerza = (.15, .48, .65, .76, .82, .86, .93, .98, 1.0)[categoria]
    propios = {c.valor_num for c in mano}
    valores_mesa = [c.valor_num for c in mesa]
    if categoria == 0:
        fuerza += max(propios) / 140
    elif categoria == 1:
        pareja = puntos[1]
        if valores_mesa.count(pareja) >= 2:
            fuerza = .23 + max(propios) / 140
        elif pareja >= max(valores_mesa):
            fuerza += .14  # Pareja alta u overpair.
        else:
            fuerza -= .06
    elif categoria == 2 and all(valores_mesa.count(v) >= 2 for v in puntos[1:3]):
        fuerza = .30 + max(propios) / 140
    elif categoria == 3 and valores_mesa.count(puntos[1]) == 3:
        fuerza = .33 + max(propios) / 140
    if len(mesa) == 5 and puntos == evaluador.puntuar_mano(mesa):
        fuerza = .35  # No confundir la jugada compartida con una ventaja propia.
        if puntos == (8, 14):
            return 1.0  # La escalera real de la mesa no puede perder.
    proyectos = proyectos_visibles(mano, mesa)
    if proyectos and categoria < 4:
        fuerza += .10 if any("en la mesa" not in p for p in proyectos) else 0
    for palo in range(4):
        if sum(c.palo_num == palo for c in mesa) >= 4 and not any(c.palo_num == palo for c in mano):
            fuerza -= .15
    return max(0, min(1, fuerza))


def decidir(s, perfil, rng):
    """Devuelve una acción legal a partir de una instantánea de información pública."""
    p = PERFILES[perfil]
    fuerza = fuerza_preflop(s.mano) if s.fase == 0 else fuerza_postflop(s.mano, s.mesa)
    posicion = -.05 if (s.posicion in ("CO", "BTN", "BTN/SB") if s.fase == 0 else s.ultimo_en_hablar) else .03
    precio = s.coste / s.bote_disputable if s.bote_disputable else 0
    presion_stack = s.coste / max(1, s.fichas)
    if s.fase == 0:
        umbral = p.entrada + posicion + .07 * s.subidas_preflop
        umbral += max(0, precio - .2) * .35 + presion_stack * .12
    else:
        umbral = .24 + (p.entrada - .5) * .7 + precio * .65
        umbral += .035 * max(0, s.rivales - 1) + .04 * s.subidas_calle + presion_stack * .08
    azar = rng.random()
    continuar = fuerza >= umbral + (azar - .5) * .08
    premium = fuerza >= .94
    if s.coste and not continuar and not premium:
        return "fold", None

    valor = fuerza >= max(.64, p.entrada + .12) if s.fase == 0 else fuerza >= .65
    apertura = s.fase == 0 and s.subidas_preflop == 0 and continuar
    farol = (not s.coste and s.rivales <= 2 and s.subidas_calle == 0
             and azar < p.farol * (1.3 if s.ultimo_en_hablar else .6))
    prob_subida = p.agresividad * (1 if valor else .65)
    subir = premium or farol or ((valor or apertura) and azar < prob_subida)
    # Tras varias resubidas, las manos medias dejan de inflar el bote.
    if s.subidas_calle >= 2 and not premium:
        subir = False
    if s.puede_subir and subir:
        maximo = s.apuesta_propia + s.fichas
        if s.fase == 0:
            objetivo = round(s.bb * (2.5 + s.limpers)) if s.subidas_preflop == 0 else s.apuesta_actual * 3
        else:
            objetivo = s.apuesta_actual + max(s.bb, round(s.bote_disputable * p.tamano))
        total = min(maximo, max(s.minimo_subida, objetivo))
        # No comprometer un stack entero por un farol o una mano marginal.
        if total - s.apuesta_propia >= s.fichas * .7 and not valor and not premium:
            return ("call" if s.coste else "check"), None
        return "raise", total
    return ("call" if s.coste else "check"), None
