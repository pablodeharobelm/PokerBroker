import random

class Usuario:
    def __init__(self, nombre, banco_inicial=10000):
        self.nombre = nombre
        self.banco = banco_inicial  

    def iniciar_sesion_mesa(self, cantidad_fichas):
        """Intenta entrar a una mesa retirando fichas de su banco general."""
        if cantidad_fichas > self.banco:
            raise ValueError("No tienes suficientes fichas en tu banco.")
        self.banco -= cantidad_fichas
        return SesionMesa(self, cantidad_fichas)

class SesionMesa:
    def __init__(self, usuario, fichas_iniciales):
        self.usuario = usuario
        self.fichas_actuales = fichas_iniciales
        self.fichas_iniciales = fichas_iniciales
        self.activa = True

    def finalizar_sesion(self):
        """Calcula el balance y devuelve las fichas restantes al banco."""
        if not self.activa:
            return 0
        balance = self.fichas_actuales - self.fichas_iniciales
        self.usuario.banco += self.fichas_actuales  
        self.activa = False
        return balance

class Carta:
    def __init__(self, valor, palo):
        self.valor = valor  
        self.palo = palo    

    def __repr__(self):
        return f"{self.valor}{self.palo}"

class Baraja:
    def __init__(self):
        valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        palos = ['♠', '♥', '♦', '♣']
        self.cartas = [Carta(v, p) for v in valores for p in palos]
        self.barajar()

    def barajar(self):
        random.shuffle(self.cartas)

    def repartir(self, cantidad):
        return [self.cartas.pop() for _ in range(cantidad)]

class GestorPosiciones:
    def __init__(self):
        # Lista oficial de posiciones para una mesa de 6 jugadores (6-Max)
        self.posiciones_6max = ["BTN", "SB", "BB", "UTG", "MP", "CO"]

    def obtener_posiciones_ronda(self, indice_dealer):
        """Calcula las posiciones de la mesa partiendo del índice del Dealer."""
        posiciones_mesa = ["" for _ in range(6)]
        for i in range(6):
            asiento_actual = (indice_dealer + i) % 6
            posiciones_mesa[asiento_actual] = self.posiciones_6max[i]
        return posiciones_mesa

class EvaluadorManos:
    def __init__(self):
        self.valores_orden = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        self.nombres_valores = {'2':'Doses', '3':'Treses', '4':'Cuatros', '5':'Cincos', '6':'Seises', '7':'Sietes', '8':'Ochos', '9':'Nueves', '10':'Dieces', 'J':'Jotas', 'Q':'Reinas', 'K':'Reyes', 'A':'Ases'}

    def evaluar_mano(self, cartas_jugador, cartas_comunitarias):
        """Combina todas las cartas disponibles y determina la mejor jugada hecha."""
        todas = cartas_jugador + cartas_comunitarias
        if not todas:
            return "Sin cartas"

        conteos_valores = {}
        conteos_palos = {}
        for c in todas:
            conteos_valores[c.valor] = conteos_valores.get(c.valor, 0) + 1
            conteos_palos[c.palo] = conteos_palos.get(c.palo, 0) + 1

        frecuencias = sorted(conteos_valores.values(), reverse=True)
        max_palo = max(conteos_palos.values()) if conteos_palos else 0

        if max_palo >= 5:
            return "Color"

        if frecuencias == 4:
            val = [v for v, c in conteos_valores.items() if c == 4]
            return f"Póker de {self.nombres_valores[val]}"

        if frecuencias == 3 and len(frecuencias) > 1 and frecuencias >= 2:
            val_trio = [v for v, c in conteos_valores.items() if c == 3]
            val_pareja = [v for v, c in conteos_valores.items() if c == 2 and v != val_trio]
            return f"Full House de {self.nombres_valores[val_trio]} y {self.nombres_valores[val_pareja]}"

        if frecuencias == 3:
            val = [v for v, c in conteos_valores.items() if c == 3]
            return f"Trío de {self.nombres_valores[val]}"

        if frecuencias == 2 and len(frecuencias) > 1 and frecuencias == 2:
            parejas = [v for v, c in conteos_valores.items() if c == 2]
            parejas = sorted(parejas, key=lambda x: self.valores_orden[x], reverse=True)
            return f"Doble Pareja de {self.nombres_valores[parejas]} y {self.nombres_valores[parejas]}"

        if frecuencias == 2:
            val = [v for v, c in conteos_valores.items() if c == 2]
            return f"Pareja de {self.nombres_valores[val]}"

        todas_ordenadas = sorted(todas, key=lambda x: self.valores_orden[x.valor], reverse=True)
        # CORREGIDO: Añadimos [0] para extraer la primera carta (la más alta) de la lista ordenada
        carta_mas_alta = todas_ordenadas[0].valor
        return f"Carta Alta ({carta_mas_alta})"

class CalculadorEquity:
    def __init__(self):
        self.evaluador = EvaluadorManos()

    def obtener_valor_numerico_jugada(self, texto_jugada):
        if "Color" in texto_jugada: return 6
        if "Póker" in texto_jugada: return 7
        if "Full House" in texto_jugada: return 5
        if "Trío" in texto_jugada: return 4
        if "Doble Pareja" in texto_jugada: return 3
        if "Pareja" in texto_jugada: return 2
        return 1

    def simular_equity_montecarlo(self, mis_cartas, cartas_mesa, simulaciones=150):
        if len(cartas_mesa) == 0:
            valores_orden = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
            # CORREGIDO: Extraemos de la lista la primera carta [0] y la segunda [1] para leer sus valores y palos
            v1 = valores_orden[mis_cartas[0].valor]
            v2 = valores_orden[mis_cartas[1].valor]
            if v1 == v2: return 35.0  
            if v1 > 10 and v2 > 10: return 22.0  
            if mis_cartas[0].palo == mis_cartas[1].palo: return 18.0 
            return 12.0  


        victorias = 0
        cartas_conocidas = set([f"{c.valor}{c.palo}" for c in mis_cartas + cartas_mesa])
        
        valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        palos = ['♠', '♥', '♦', '♣']
        todas_cartas_posibles = [Carta(v, p) for v in valores for p in palos]
        cartas_restantes = [c for c in todas_cartas_posibles if f"{c.valor}{c.palo}" not in cartas_conocidas]

        for _ in range(simulaciones):
            pool = cartas_restantes.copy()
            random.shuffle(pool)

            mesa_simulada = cartas_mesa.copy()
            while len(mesa_simulada) < 5:
                mesa_simulada.append(pool.pop())

            cartas_rival = [pool.pop(), pool.pop()]

            mi_jugada = self.evaluador.evaluar_mano(mis_cartas, mesa_simulada)
            rival_jugada = self.evaluador.evaluar_mano(cartas_rival, mesa_simulada)

            mi_score = self.obtener_valor_numerico_jugada(mi_jugada)
            rival_score = self.obtener_valor_numerico_jugada(rival_jugada)

            if mi_score > rival_score:
                victorias += 1
            elif mi_score == rival_score:
                victorias += 0.5 

        return round((victorias / simulaciones) * 100, 1)

class TrackerEstadisticasBots:
    """Clase encargada de simular y guardar el historial estadístico del HUD de los rivales."""
    def __init__(self):
        # ESTRATEGIA DE CONTINGENCIA INMUNE: Construimos las listas vacías llamando al comando list() 
        # y rellenando los tres ceros mediante appends numéricos puros. Evita cualquier corchete.
        self.historial = dict()
        
        for bot in ["peco246", "Breta232", "Davidkim", "_Yurec0816", "FAKEL382"]:
            lista_vacia = list()
            lista_vacia.append(0)  # Manos Totales
            lista_vacia.append(0)  # Veces VPIP
            lista_vacia.append(0)  # Veces PFR
            self.historial[bot] = lista_vacia
            
        self.perfiles = {
            "peco246": {"vpip": 22, "pfr": 17},     
            "Breta232": {"vpip": 14, "pfr": 8},     
            "Davidkim": {"vpip": 45, "pfr": 32},    
            "_Yurec0816": {"vpip": 38, "pfr": 10},   
            "FAKEL382": {"vpip": 25, "pfr": 19}     
        }

    def simular_mano_y_calcular_hud(self, nombre_bot):
        if nombre_bot not in self.historial:
            return "V: --% | P: --%"
            
        stats = self.historial[nombre_bot]
        stats[0] += 1  # Incrementa Manos Totales
        
        entro_al_bote = random.randint(1, 100) <= self.perfiles[nombre_bot]["vpip"]
        subio_preflop = entro_al_bote and (random.randint(1, 100) <= (self.perfiles[nombre_bot]["pfr"] / self.perfiles[nombre_bot]["vpip"] * 100))
        
        if entro_al_bote: stats[1] += 1  # Incrementa Veces VPIP
        if subio_preflop: stats[2] += 1  # Incrementa Veces PFR
        
        vpip_porcentaje = round((stats[1] / stats[0]) * 100)
        pfr_porcentaje = round((stats[2] / stats[0]) * 100)
        
        return f"V: {vpip_porcentaje}% | P: {pfr_porcentaje}%"
