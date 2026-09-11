import unittest
from estadisticas import DEFINICIONES
from rangos_estadisticas import RANGOS, interpretar


class RangosTests(unittest.TestCase):
    def test_cobertura_y_limites(self):
        self.assertEqual(set(RANGOS), set(DEFINICIONES))
        for clave, (bajo, alto, textos) in RANGOS.items():
            self.assertTrue(0 < bajo < alto < 100)
            self.assertEqual(interpretar(clave, None), "Sin oportunidades")
            self.assertEqual(interpretar(clave, 0), textos[0])
            self.assertEqual(interpretar(clave, bajo), textos[1])
            self.assertEqual(interpretar(clave, alto), textos[1])
            self.assertEqual(interpretar(clave, 100), textos[2])

    def test_cien_por_ciento_no_se_presenta_como_perfeccion(self):
        self.assertEqual(interpretar("VPIP", 100), "Entras muy a menudo")
        self.assertEqual(interpretar("RIVER-FOLD", 100), "Abandonas a menudo")
        self.assertEqual(interpretar("WSD", 100), "Cobras muchos showdowns")
