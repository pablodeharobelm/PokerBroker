import random
import unittest

from logica_poker import Baraja, Carta, EvaluadorManos, GestorPosiciones
from motor_mesa import JugadorMesa, MotorMesa


def cartas(texto):
    valores = {"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return [Carta(valores[c[0]] if c[0] in valores else int(c[0]), "shdc".index(c[1]))
            for c in texto.split()]


def mesa(fichas=(1000, 1000, 1000), semilla=1):
    m = MotorMesa([JugadorMesa(str(i), f) for i, f in enumerate(fichas)], rng=random.Random(semilla))
    m.iniciar_mano()
    return m


class EvaluadorTests(unittest.TestCase):
    def setUp(self):
        self.e = EvaluadorManos()

    def puntos(self, texto):
        return self.e.puntuar_mano(cartas(texto))

    def test_todas_las_categorias(self):
        ejemplos = ["As Kh 9d 5c 3s", "As Ah 9d 5c 3s", "As Ah 9d 9c 3s",
                    "As Ah Ad 5c 3s", "As 2h 3d 4c 5s", "As Js 9s 5s 3s",
                    "As Ah Ad 5c 5s", "As Ah Ad Ac 3s", "9s Ts Js Qs Ks"]
        for categoria, mano in enumerate(ejemplos):
            with self.subTest(mano=mano):
                self.assertEqual(self.puntos(mano)[0], categoria)

    def test_dos_trios_forman_full(self):
        self.assertEqual(self.puntos("As Ah Ad Ks Kh Kd 2s"), (6, 14, 13))

    def test_mejores_cinco_y_tres_parejas(self):
        self.assertEqual(self.puntos("As Ah Ks Kh Qs Qh Jd"), (2, 14, 13, 12))

    def test_kickers_y_empate_mesa(self):
        board = cartas("As Ah 9d 5c 3s")
        self.assertGreater(self.e.puntuar_mano(cartas("Kd Qh"), board), self.e.puntuar_mano(cartas("Jd Th"), board))
        board = cartas("As Ks Qs Js Ts")
        self.assertEqual(self.e.puntuar_mano(cartas("2h 3h"), board), self.e.puntuar_mano(cartas("Ad Ac"), board))

    def test_as_bajo_y_color_no_es_escalera_color(self):
        self.assertLess(self.puntos("As 2h 3d 4c 5s"), self.puntos("2s 3h 4d 5c 6s"))
        self.assertEqual(self.puntos("As Ks Qs 9s 2s Jh Td")[0], 5)

    def test_duplicados_rechazados(self):
        with self.assertRaises(ValueError):
            self.puntos("As As")

    def test_baraja_no_reparte_parcialmente(self):
        b = Baraja()
        with self.assertRaises(ValueError):
            b.repartir(53)
        self.assertEqual(len(b.cartas), 52)
        self.assertEqual(len({(c.valor_num, c.palo_num) for c in b.repartir(52)}), 52)


class MesaTests(unittest.TestCase):
    def test_ciega_all_in_no_exige_pago_sin_rival(self):
        m = mesa((1000, 10))
        self.assertIsNone(m.turno)
        self.assertEqual(m.por_pagar(0), 0)
        for _ in range(4):
            m.avanzar_calle()
        self.assertEqual(m.devoluciones, {0: 10})
        self.assertEqual(sum(m.pagos.values()), 20)
        self.assertEqual(sum(j.fichas for j in m.jugadores), 1010)

    def test_ciega_all_in_solo_se_iguala_por_su_importe(self):
        m = mesa((1000, 30))
        self.assertEqual(m.turno, 0)
        self.assertEqual(m.por_pagar(0), 10)
        m.actuar(0, "call")
        self.assertEqual(m.bote, 60)
        self.assertIsNone(m.turno)
        # Con dos jugadores capaces de apostar se mantiene la ciega nominal.
        m = mesa((1000, 1000, 30))
        self.assertEqual(m.por_pagar(0), 40)

    def test_ciegas_deben_ser_fichas_enteras(self):
        for sb, bb in [(True, 40), (20, 40.5), (0, 40)]:
            with self.assertRaises(ValueError):
                MotorMesa([JugadorMesa("a", 100), JugadorMesa("b", 100)], sb, bb)

    def test_ciegas_posiciones_y_orden(self):
        m = mesa((1000,) * 6)
        self.assertEqual(m.bote, 60)
        self.assertEqual([j.posicion for j in m.jugadores], ["BTN", "SB", "BB", "UTG", "MP", "CO"])
        self.assertEqual(m.turno, 3)
        for i in (3, 4, 5, 0, 1):
            self.assertEqual(m.turno, i)
            m.actuar(i, "call")
        self.assertEqual(m.turno, 2)  # La BB mantiene su opción.
        m.actuar(2, "check")
        self.assertIsNone(m.turno)
        self.assertEqual(m.fase, 0)
        m.avanzar_calle()
        self.assertEqual(len(m.comunitarias), 3)
        self.assertEqual(m.turno, 1)

    def test_posicion_dealer(self):
        for dealer in range(6):
            posiciones = GestorPosiciones().obtener_posiciones_ronda(dealer)
            self.assertEqual(posiciones[dealer], "BTN")
            self.assertEqual(posiciones[(dealer + 1) % 6], "SB")

    def test_heads_up_orden(self):
        m = mesa((1000, 1000))
        self.assertEqual(m.turno, 0)
        self.assertEqual(m.jugadores[0].posicion, "BTN/SB")
        m.actuar(0, "call")
        m.actuar(1, "check")
        m.avanzar_calle()
        self.assertEqual(m.turno, 1)

    def test_call_y_raise_descontar_diferencia(self):
        m = mesa()
        m.actuar(0, "raise", 100)
        m.actuar(1, "call")
        self.assertEqual(m.jugadores[1].fichas, 900)
        m.actuar(2, "raise", 200)
        self.assertEqual(m.jugadores[2].fichas, 800)
        self.assertEqual(m.minimo_subida(), 300)
        m.actuar(0, "call")
        m.actuar(1, "call")
        self.assertEqual(m.bote, 600)

    def test_acciones_invalidas_no_mutan(self):
        m = mesa()
        for indice, accion, total in [(1, "call", None), (0, "check", None), (0, "raise", 50), (0, "raise", 1001)]:
            with self.assertRaises(ValueError):
                m.actuar(indice, accion, total)
        self.assertEqual(m.bote, 60)
        self.assertEqual(m.turno, 0)
        with self.assertRaises(ValueError):
            m.avanzar_calle()

    def test_all_in_corto_no_reabre(self):
        m = mesa((1000, 130, 1000))
        m.actuar(0, "raise", 100)
        m.actuar(1, "raise", 130)
        m.actuar(2, "call")
        self.assertEqual(m.turno, 0)
        self.assertFalse(m.puede_subir(0))
        self.assertEqual(m.minimo_subida(), 190)
        m.actuar(0, "call")
        self.assertIsNone(m.turno)

    def test_all_ins_cortos_acumulados_reabren(self):
        m = mesa((130, 160, 1000, 1000))
        m.actuar(3, "raise", 100)
        m.actuar(0, "raise", 130)
        m.actuar(1, "raise", 160)
        m.actuar(2, "call")
        self.assertEqual(m.turno, 3)
        self.assertTrue(m.puede_subir(3))
        self.assertEqual(m.minimo_subida(), 220)

    def test_all_in_call_limitado_y_devolucion(self):
        m = mesa((100, 1000))
        m.actuar(0, "raise", 100)
        self.assertFalse(m.puede_subir(1))
        m.actuar(1, "call")
        for _ in range(4):
            m.avanzar_calle()
        self.assertTrue(m.terminada)
        self.assertEqual(sum(j.fichas for j in m.jugadores), 1100)

    def test_botes_secundarios_y_exceso_devuelto(self):
        m = mesa((100, 200, 300))
        m.actuar(0, "raise", 100)
        m.actuar(1, "raise", 200)
        m.actuar(2, "call")
        m.jugadores[0].cartas = cartas("As Ah")
        m.jugadores[1].cartas = cartas("Ks Kh")
        m.jugadores[2].cartas = cartas("Qs Qh")
        m.comunitarias = cartas("2s 3h 7d 8c 9s")
        m.fase = 3
        m.avanzar_calle()
        self.assertEqual(m.pagos, {0: 300, 1: 200})
        self.assertEqual([j.fichas for j in m.jugadores], [300, 200, 100])

    def test_raise_sin_igualar_se_devuelve(self):
        m = mesa()
        m.actuar(0, "raise", 300)
        m.actuar(1, "fold")
        m.actuar(2, "fold")
        self.assertTrue(m.terminada)
        self.assertEqual(m.devoluciones, {0: 260})
        self.assertEqual([j.fichas for j in m.jugadores], [1060, 980, 960])
        with self.assertRaises(ValueError):
            m.actuar(0, "fold")

    def test_call_mayor_que_stack_y_varios_botes(self):
        m = mesa((1000, 100, 200))
        m.actuar(0, "raise", 300)
        m.actuar(1, "call")
        m.actuar(2, "call")
        self.assertEqual([j.fichas for j in m.jugadores], [700, 0, 0])
        self.assertIsNone(m.turno)
        for _ in range(4):
            m.avanzar_calle()
        self.assertEqual(m.devoluciones, {0: 100})
        self.assertEqual(sum(m.pagos.values()), 500)
        self.assertEqual(sum(j.fichas for j in m.jugadores), 1300)

    def test_empate_ficha_impar_izquierda_dealer(self):
        m = mesa((100, 100, 100))
        # Bote de 123 con una aportación muerta y dos ganadores empatados.
        for j in m.jugadores:
            j.aportado = 41
            j.fichas = 59
        m.bote = 123
        m.jugadores[2].retirado = True
        m.jugadores[0].cartas = cartas("2h 3h")
        m.jugadores[1].cartas = cartas("4h 5h")
        m.comunitarias = cartas("As Ks Qs Js Ts")
        m.fase = 3
        m.turno = None
        m.avanzar_calle()
        self.assertEqual(m.pagos, {1: 62, 0: 61})
        self.assertEqual(sum(j.fichas for j in m.jugadores), 300)

    def test_empate_principal_ganador_secundario_y_devolucion(self):
        m = mesa((50, 100, 100, 300))
        m.actuar(3, "raise", 200)
        for i in (0, 1, 2):
            m.actuar(i, "call")
        for j, mano in zip(m.jugadores, ("As 3h", "Ah 4h", "Ts 6h", "8s 7h")):
            j.cartas = cartas(mano)
        m.comunitarias = cartas("Ks Kh Qd Jc 2s")
        m.fase = 3
        m.avanzar_calle()
        self.assertEqual(m.resultados, [(200, [1, 0]), (150, [1])])
        self.assertEqual(m.pagos, {0: 100, 1: 250})
        self.assertEqual(m.devoluciones, {3: 100})
        self.assertEqual([j.fichas for j in m.jugadores], [100, 250, 0, 200])

    def test_dealer_rota_y_omite_jugadores_sin_fichas(self):
        m = mesa((1000, 0, 1000, 1000))
        while not m.terminada:
            m.actuar(m.turno, "fold")
        m.iniciar_mano()
        self.assertEqual(m.dealer, 2)
        self.assertEqual(m.jugadores[1].cartas, [])

    def test_simulacion_conserva_fichas_y_cartas(self):
        for semilla in range(100):
            m = mesa((80, 130, 270, 700, 1000, 1500), semilla)
            inicial = sum(j.fichas + j.aportado for j in m.jugadores)
            pasos = 0
            while not m.terminada:
                if m.turno is None:
                    m.avanzar_calle()
                else:
                    accion, total = m.decidir_bot()
                    m.actuar(m.turno, accion, total)
                pasos += 1
                self.assertLess(pasos, 200)
                self.assertTrue(all(j.fichas >= 0 for j in m.jugadores))
                self.assertEqual(sum(j.fichas for j in m.jugadores) + m.bote, inicial)
                conocidas = m.comunitarias + [c for j in m.jugadores for c in j.cartas]
                self.assertEqual(len(conocidas), len({(c.valor_num, c.palo_num) for c in conocidas}))


if __name__ == "__main__":
    unittest.main()
