"""Estado y reglas de una mesa No-Limit Hold'em, sin dependencias de Qt.

Los índices de asientos siguen el sentido horario. Los raises se expresan
como aportación TOTAL en la calle; los calls descuentan solo la diferencia.
"""

from dataclasses import dataclass, field
import random
from datetime import datetime, timezone
from uuid import uuid4

from logica_poker import Baraja, EvaluadorManos
from estrategia_bots import SituacionBot, decidir


@dataclass
class JugadorMesa:
    nombre: str
    fichas: int
    cartas: list = field(default_factory=list)
    posicion: str = ""
    retirado: bool = False
    participando: bool = False
    aportado: int = 0
    apuesta: int = 0
    accion: str = ""
    ultima_apuesta_vista: int | None = None
    perfil: str = "equilibrado"


class MotorMesa:
    CALLES = ("Preflop", "Flop", "Turn", "River")

    def __init__(self, jugadores, ciega_pequena=20, ciega_grande=40, rng=None):
        if not 2 <= len(jugadores) <= 6:
            raise ValueError("La mesa admite de dos a seis jugadores.")
        if any(type(j.fichas) is not int or j.fichas < 0 for j in jugadores):
            raise ValueError("Las fichas deben ser enteros no negativos.")
        if (type(ciega_pequena) is not int or type(ciega_grande) is not int
                or not 0 < ciega_pequena <= ciega_grande):
            raise ValueError("Ciegas inválidas.")
        self.jugadores = jugadores
        self.sb = ciega_pequena
        self.bb = ciega_grande
        self.rng = rng or random.Random()
        self.dealer = -1
        self.terminada = True
        self.turno = None
        self.comunitarias = []
        self.fase = 0
        self.bote = 0
        self.pagos = {}
        self.devoluciones = {}
        self.resultados = []

    def _orden(self, despues):
        return [(despues + n) % len(self.jugadores) for n in range(1, len(self.jugadores) + 1)]

    def vivos(self):
        return [i for i, j in enumerate(self.jugadores) if j.participando and not j.retirado]

    def _con_fichas(self):
        return [i for i in self.vivos() if self.jugadores[i].fichas > 0]

    def iniciar_mano(self):
        if not self.terminada:
            raise ValueError("La mano anterior todavía está en curso.")
        activos = [i for i, j in enumerate(self.jugadores) if j.fichas > 0]
        if len(activos) < 2:
            raise ValueError("No quedan dos jugadores con fichas.")
        self.dealer_anterior = self.dealer
        self.dealer = next(i for i in self._orden(self.dealer) if i in activos)
        orden = [self.dealer] + [i for i in self._orden(self.dealer) if i in activos and i != self.dealer]
        etiquetas = {
            2: ["BTN/SB", "BB"], 3: ["BTN", "SB", "BB"],
            4: ["BTN", "SB", "BB", "CO"],
            5: ["BTN", "SB", "BB", "UTG", "CO"],
            6: ["BTN", "SB", "BB", "UTG", "MP", "CO"],
        }[len(activos)]
        self.rng_inicio = self.rng.getstate()
        self.baraja = Baraja(self.rng)
        self.id_mano = str(uuid4())
        self.inicio_mano = datetime.now(timezone.utc).isoformat()
        self.fichas_iniciales = [j.fichas for j in self.jugadores]
        self.comunitarias = []
        self.fase = 0
        self.bote = 0
        self.terminada = False
        self.showdown = False
        self.pagos, self.devoluciones, self.resultados = {}, {}, []
        self.eventos = []
        self.subidas_preflop = 0
        self.vieron_flop = set()
        for i, j in enumerate(self.jugadores):
            j.cartas = []
            j.participando = i in activos
            j.retirado = False
            j.aportado = j.apuesta = 0
            j.posicion = etiquetas[orden.index(i)] if i in activos else "Fuera"
            j.accion = "" if i in activos else "Sin fichas"
            j.ultima_apuesta_vista = None
        for _ in range(2):
            for i in self._orden(self.dealer):
                if i in activos:
                    self.jugadores[i].cartas.extend(self.baraja.repartir(1))
        indice_sb = orden[0] if len(activos) == 2 else orden[1]
        indice_bb = orden[1] if len(activos) == 2 else orden[2]
        self._poner(indice_sb, min(self.sb, self.jugadores[indice_sb].fichas))
        self._poner(indice_bb, min(self.bb, self.jugadores[indice_bb].fichas))
        self.ciegas_puestas = [{"jugador": i, "cantidad": self.jugadores[i].apuesta,
                               "tipo": tipo} for i, tipo in ((indice_sb, "SB"), (indice_bb, "BB"))]
        self.jugadores[indice_sb].accion = "Ciega pequeña"
        self.jugadores[indice_bb].accion = "Ciega grande"
        self.apuesta_actual = self.bb
        self.ultima_subida = self.bb
        self.pendientes = set(self._con_fichas())
        self._seleccionar_turno(indice_bb)

    def _poner(self, indice, cantidad):
        j = self.jugadores[indice]
        j.fichas -= cantidad
        j.apuesta += cantidad
        j.aportado += cantidad
        self.bote += cantidad

    def por_pagar(self, indice):
        objetivo = self.apuesta_actual
        # Una ciega all-in inferior a la nominal no obliga al único jugador
        # con fichas a pagar dinero que ningún rival puede disputar.
        if self._con_fichas() == [indice]:
            objetivo = min(objetivo, max((self.jugadores[i].apuesta
                                         for i in self.vivos() if i != indice), default=0))
        return max(0, objetivo - self.jugadores[indice].apuesta)

    def puede_subir(self, indice):
        j = self.jugadores[indice]
        reabierta = (j.ultima_apuesta_vista is None or
                     self.apuesta_actual - j.ultima_apuesta_vista >= self.ultima_subida)
        return (not self.terminada and self.turno == indice and reabierta
                and j.apuesta + j.fichas > self.apuesta_actual
                and any(k != indice for k in self._con_fichas()))

    def minimo_subida(self):
        return self.apuesta_actual + self.ultima_subida if self.apuesta_actual else self.bb

    def actuar(self, indice, accion, total=None):
        if self.terminada or self.turno != indice:
            raise ValueError("No es el turno de ese jugador.")
        j = self.jugadores[indice]
        deuda = self.por_pagar(indice)
        subida_previa = self.subidas_preflop
        podia_subir = self.puede_subir(indice)
        bote_previo = self.bote
        cantidad = 0
        if accion == "fold":
            j.retirado = True
            j.accion = "Fold"
        elif accion in ("check", "call"):
            if accion == "check" and deuda:
                raise ValueError("Debes igualar la apuesta o retirarte.")
            cantidad = min(deuda, j.fichas)
            self._poner(indice, cantidad)
            j.accion = f"Call {cantidad}" if cantidad else "Check"
        elif accion == "raise":
            if not self.puede_subir(indice):
                raise ValueError("La apuesta no está abierta para una subida.")
            maximo = j.apuesta + j.fichas
            if type(total) is not int or not self.apuesta_actual < total <= maximo:
                raise ValueError("Importe de subida inválido.")
            if total < self.minimo_subida() and total != maximo:
                raise ValueError("Solo un all-in puede ser inferior a la subida mínima.")
            incremento = total - self.apuesta_actual
            cantidad = total - j.apuesta
            self._poner(indice, cantidad)
            if incremento >= self.ultima_subida:
                self.ultima_subida = incremento
            self.apuesta_actual = total
            self.pendientes.update(k for k in self._con_fichas() if k != indice and self.por_pagar(k))
            j.accion = f"Sube a {total}"
            if self.fase == 0:
                self.subidas_preflop += 1
        else:
            raise ValueError("Acción desconocida.")
        if not j.fichas and not j.retirado:
            j.accion += " · All-in"
        j.ultima_apuesta_vista = self.apuesta_actual
        self.eventos.append({"jugador": indice, "fase": self.fase, "accion": accion,
                             "cantidad": cantidad, "subidas_previas": subida_previa,
                             "por_pagar": deuda, "podia_subir": podia_subir,
                             "bote_previo": bote_previo, "bote_despues": self.bote,
                             "total_calle": j.apuesta, "fichas_restantes": j.fichas,
                             "all_in": not j.fichas and not j.retirado})
        self.pendientes.discard(indice)
        self._seleccionar_turno(indice)

    def _seleccionar_turno(self, despues):
        self.turno = None
        if len(self.vivos()) == 1:
            self._resolver()
            return
        con_fichas = self._con_fichas()
        self.pendientes.intersection_update(con_fichas)
        # No se permite apostar contra rivales que ya están todos all-in.
        if len(con_fichas) == 1 and not self.por_pagar(con_fichas[0]):
            self.pendientes.clear()
        self.turno = next((i for i in self._orden(despues) if i in self.pendientes), None)

    def avanzar_calle(self):
        if self.terminada or self.turno is not None:
            raise ValueError("Hay acciones pendientes o la mano ya terminó.")
        if self.fase == 3:
            self._resolver()
            return
        self.fase += 1
        self.baraja.repartir(1)  # Carta quemada.
        self.comunitarias.extend(self.baraja.repartir(3 if self.fase == 1 else 1))
        if self.fase == 1:
            self.vieron_flop = set(self.vivos())
        self.apuesta_actual = 0
        self.ultima_subida = self.bb
        for j in self.jugadores:
            j.apuesta = 0
            j.ultima_apuesta_vista = None
            if j.participando and not j.retirado:
                j.accion = "All-in" if not j.fichas else ""
        self.pendientes = set(self._con_fichas())
        self._seleccionar_turno(self.dealer)

    def _resolver(self):
        vivos = self.vivos()
        self.showdown = len(vivos) > 1
        if self.showdown and len(self.comunitarias) != 5:
            raise ValueError("Faltan cartas para el showdown.")
        evaluador = EvaluadorManos()
        puntos = {i: evaluador.puntuar_mano(self.jugadores[i].cartas, self.comunitarias)
                  for i in vivos} if self.showdown else {}
        anterior = 0
        # Cada nivel de aportación genera un bote independiente y sus elegibles.
        for nivel in sorted({j.aportado for j in self.jugadores if j.aportado}):
            aportantes = [i for i, j in enumerate(self.jugadores) if j.aportado >= nivel]
            cantidad = (nivel - anterior) * len(aportantes)
            anterior = nivel
            if len(aportantes) == 1:
                i = aportantes[0]
                self.devoluciones[i] = self.devoluciones.get(i, 0) + cantidad
                continue
            elegibles = [i for i in vivos if i in aportantes]
            if not self.showdown:
                ganadores = vivos
            else:
                mejor = max(puntos[i] for i in elegibles)
                ganadores = [i for i in self._orden(self.dealer) if i in elegibles and puntos[i] == mejor]
            parte, resto = divmod(cantidad, len(ganadores))
            for n, i in enumerate(ganadores):
                self.pagos[i] = self.pagos.get(i, 0) + parte + (n < resto)
            self.resultados.append((cantidad, ganadores))
        for i, cantidad in self.pagos.items():
            self.jugadores[i].fichas += cantidad
        for i, cantidad in self.devoluciones.items():
            self.jugadores[i].fichas += cantidad
        self.bote = 0
        self.terminada = True
        self.turno = None
        self.pendientes.clear()

    def decidir_bot(self):
        """Entrega al bot únicamente su mano y el estado público de las apuestas."""
        i = self.turno
        if i is None:
            raise ValueError("No hay un turno pendiente.")
        j = self.jugadores[i]
        coste = min(self.por_pagar(i), j.fichas)
        limite = j.aportado + coste
        bote = sum(min(r.aportado, limite) for r in self.jugadores) + coste if coste else self.bote
        orden = [k for k in self._orden(self.dealer) if k in self._con_fichas()]
        situacion = SituacionBot(
            mano=tuple(j.cartas), mesa=tuple(self.comunitarias), posicion=j.posicion,
            fase=self.fase, fichas=j.fichas, apuesta_propia=j.apuesta,
            apuesta_actual=self.apuesta_actual, coste=coste, bote_disputable=bote,
            bb=self.bb, minimo_subida=self.minimo_subida(), puede_subir=self.puede_subir(i),
            rivales=len(self.vivos()) - 1, subidas_preflop=self.subidas_preflop,
            subidas_calle=sum(e["accion"] == "raise" and e["fase"] == self.fase for e in self.eventos),
            limpers=len({e["jugador"] for e in self.eventos if e["fase"] == 0 and e["accion"] == "call" and e["subidas_previas"] == 0}),
            ultimo_en_hablar=bool(orden) and orden[-1] == i)
        return decidir(situacion, j.perfil, self.rng)
