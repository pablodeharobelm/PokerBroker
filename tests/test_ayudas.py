import unittest
from ayudas_poker import proyectos_visibles, referencia_call
from test_motor import cartas


class AyudasTests(unittest.TestCase):
    def test_call_normal_y_all_in(self):
        self.assertEqual(referencia_call(50, [50, 100], 0)["porcentaje"], 25)
        dato = referencia_call(50, [50, 300, 300], 0)
        self.assertTrue(dato["botes_limitados"])
        self.assertEqual(dato["bote_elegible"], 300)
        self.assertAlmostEqual(dato["porcentaje"], 100 / 6)
        self.assertIsNone(referencia_call(0, [40, 40], 0)["porcentaje"])
        self.assertIsNone(referencia_call(40, [0, 20], 0)["porcentaje"])

    def test_color_y_sin_backdoor(self):
        self.assertEqual(proyectos_visibles(cartas("As Js"), cartas("2s 8s Kh")), ["Color (picas)"])
        self.assertEqual(proyectos_visibles(cartas("As Js"), cartas("2s 8h Kh")), [])
        self.assertEqual(proyectos_visibles(cartas("As Js"), cartas("2s 8s Ks")), [])

    def test_escaleras_y_as(self):
        self.assertIn("abierta (4/9)", proyectos_visibles(cartas("5s 6h"), cartas("7d 8c Ks"))[0])
        self.assertIn("interna (7)", proyectos_visibles(cartas("5s 6h"), cartas("8d 9c Ks"))[0])
        self.assertIn("interna (5)", proyectos_visibles(cartas("As 2h"), cartas("3d 4c Ks"))[0])
        self.assertIn("interna (10)", proyectos_visibles(cartas("As Jh"), cartas("Qd Kc 2s"))[0])
        self.assertIn("doble interna (5/9)", proyectos_visibles(cartas("4s 6h"), cartas("7d 8c Ts"))[0])

    def test_mesa_compartida_y_river(self):
        self.assertIn("en la mesa", proyectos_visibles(cartas("2h Ks"), cartas("5d 6c 7s 8h"))[0])
        self.assertIn("en la mesa", proyectos_visibles(cartas("2h Kd"), cartas("3s 6s 8s Js"))[0])
        self.assertEqual(proyectos_visibles(cartas("5s 6h"), cartas("7d 8c 9s")), [])
        self.assertEqual(proyectos_visibles(cartas("5s 6h"), []), [])
        self.assertEqual(proyectos_visibles(cartas("5s 6h"), cartas("7d 8c Ks 2d Qs")), [])
