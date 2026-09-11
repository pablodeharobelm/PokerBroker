from dataclasses import replace
import random
import unittest

from estrategia_bots import PERFILES, SituacionBot, decidir, fuerza_preflop, fuerza_postflop
from test_motor import cartas, mesa


def situacion(mano="As Qs", **cambios):
    s = SituacionBot(tuple(cartas(mano)), (), "BTN", 0, 1000, 0, 40, 40, 100,
                     40, 80, True, 2, 0, 0, 0, True)
    return replace(s, **cambios)


class AzarMedio:
    def random(self):
        return .5


class BotsTests(unittest.TestCase):
    def test_fuerza_inicial_distingue_premium_y_conectores(self):
        self.assertGreater(fuerza_preflop(cartas("As Ah")), fuerza_preflop(cartas("As Ks")))
        self.assertGreater(fuerza_preflop(cartas("As Ks")), fuerza_preflop(cartas("7s 2h")))
        self.assertGreater(fuerza_preflop(cartas("9s 8s")), fuerza_preflop(cartas("9s 8h")))

    def test_estilos_tienen_frecuencias_distintas(self):
        frecuencias = {}
        for perfil in PERFILES:
            rng = random.Random(17)
            frecuencias[perfil] = sum(decidir(situacion(), perfil, rng)[0] == "raise" for _ in range(400))
        self.assertGreater(frecuencias["agresivo"], frecuencias["equilibrado"])
        self.assertGreater(frecuencias["equilibrado"], frecuencias["conservador"])
        self.assertGreater(frecuencias["conservador"], frecuencias["pagador"])
        marginal = situacion("Ks 8h")
        self.assertEqual(decidir(marginal, "conservador", AzarMedio())[0], "fold")
        self.assertEqual(decidir(marginal, "pagador", AzarMedio())[0], "call")

    def test_precio_y_posicion_cambian_la_decision(self):
        s = situacion("Ks 8h", posicion="BTN", coste=20, bote_disputable=300)
        self.assertNotEqual(decidir(s, "equilibrado", AzarMedio())[0], "fold")
        self.assertEqual(decidir(replace(s, posicion="UTG"), "equilibrado", AzarMedio())[0], "fold")
        barato = situacion("8s 8h", mesa=tuple(cartas("Kd 7c 2s")), fase=1,
                          coste=20, bote_disputable=400, rivales=1)
        caro = replace(barato, coste=800, bote_disputable=1800, subidas_calle=2)
        self.assertEqual(decidir(barato, "equilibrado", AzarMedio())[0], "call")
        self.assertEqual(decidir(caro, "equilibrado", AzarMedio())[0], "fold")

    def test_pareja_mesa_no_equivale_a_pareja_alta(self):
        compartida = fuerza_postflop(cartas("As 9h"), cartas("Kd Kc 2s"))
        propia = fuerza_postflop(cartas("Ks 9h"), cartas("Kd 7c 2s"))
        self.assertLess(compartida, propia)

    def test_no_fold_si_puede_pasar_y_no_raise_si_prohibido(self):
        for perfil in PERFILES:
            for seed in range(20):
                accion, _ = decidir(situacion("7s 2h", coste=0), perfil, random.Random(seed))
                self.assertNotEqual(accion, "fold")
                accion, _ = decidir(situacion("As Ah", puede_subir=False), perfil, random.Random(seed))
                self.assertEqual(accion, "call")

    def test_cartas_ocultas_y_baraja_no_afectan_decision(self):
        m = mesa()
        rng = m.rng.getstate()
        esperado = m.decidir_bot()
        for i, j in enumerate(m.jugadores):
            if i != m.turno:
                j.cartas = None
        m.baraja = None
        m.rng.setstate(rng)
        self.assertEqual(m.decidir_bot(), esperado)

    def test_perfiles_juegan_manos_legales_y_conservan_fichas(self):
        for seed in range(60):
            m = mesa((80, 130, 270, 700, 1000, 1500), seed)
            for i, j in enumerate(m.jugadores):
                j.perfil = list(PERFILES)[i % 4]
            pasos = 0
            while not m.terminada:
                if m.turno is None:
                    m.avanzar_calle()
                else:
                    accion, total = m.decidir_bot()
                    m.actuar(m.turno, accion, total)
                pasos += 1
                self.assertLess(pasos, 200)
                self.assertEqual(sum(j.fichas for j in m.jugadores) + m.bote, 3680)
                self.assertTrue(all(j.fichas >= 0 for j in m.jugadores))
