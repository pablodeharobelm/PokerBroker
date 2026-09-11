import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from equity import estimar_equity
from sesion_guardada import ArchivoSesion, ErrorSesion, instantanea, recuperar
from estadisticas import construir_registro
from persistencia import BaseDatosLocal
from test_motor import mesa


def par(cartas):
    return [(c.valor_num, c.palo_num) for c in cartas]


class EquityTests(unittest.TestCase):
    def test_empate_mesa_reparte_equity(self):
        mesa_royal = ((10, 0), (11, 0), (12, 0), (13, 0), (14, 0))
        for rivales in (1, 2, 5):
            dato = estimar_equity(((2, 1), (3, 1)), mesa_royal, rivales, muestras=60, semilla=1)
            self.assertAlmostEqual(dato["porcentaje"], 100 / (rivales + 1))

    def test_nuts_y_perdida_segura(self):
        dato = estimar_equity(((14, 0), (13, 0)), ((12, 0), (11, 0), (10, 0), (2, 1), (3, 1)), 2, 60, 1)
        self.assertEqual(dato["porcentaje"], 100)
        dato = estimar_equity(((2, 0), (3, 0)), ((14, 1), (14, 2), (14, 3), (14, 0), (13, 1)), 1, 60, 1)
        self.assertEqual(dato["porcentaje"], 50)  # Póker y K de la mesa: empate.

    def test_aa_supera_mano_debil_y_es_reproducible(self):
        premium = estimar_equity(((14, 0), (14, 1)), (), 1, 250, 12)
        debil = estimar_equity(((7, 0), (2, 1)), (), 1, 250, 12)
        self.assertGreater(premium["porcentaje"], debil["porcentaje"] + 30)
        self.assertEqual(premium, estimar_equity(((14, 0), (14, 1)), (), 1, 250, 12))

    def test_cancelacion_y_entradas_invalidas(self):
        cancelar = Event()
        cancelar.set()
        self.assertIsNone(estimar_equity(((14, 0), (14, 1)), (), 1, cancelar=cancelar))
        with self.assertRaises(ValueError):
            estimar_equity(((14, 0), (14, 0)), (), 1)
        with self.assertRaises(ValueError):
            estimar_equity(((14, 0), (14, 1)), (), 6)


class SesionTests(unittest.TestCase):
    def copiar(self, motor, registrada=False, pendiente=None):
        datos = json.loads(json.dumps(instantanea(motor, registrada, False, pendiente)))
        return recuperar(datos), datos

    def comprobar_igual(self, a, b):
        self.assertEqual(a.eventos, b.eventos)
        self.assertEqual(a.turno, b.turno)
        self.assertEqual(a.pendientes, b.pendientes)
        self.assertEqual(a.bote, b.bote)
        self.assertEqual(a.ultima_subida, b.ultima_subida)
        self.assertEqual(a.id_mano, b.id_mano)
        self.assertEqual(par(a.baraja.cartas), par(b.baraja.cartas))
        self.assertEqual(par(a.comunitarias), par(b.comunitarias))
        self.assertEqual([j.fichas for j in a.jugadores], [j.fichas for j in b.jugadores])
        self.assertEqual([par(j.cartas) for j in a.jugadores], [par(j.cartas) for j in b.jugadores])

    def test_recuperar_cada_accion_calle_y_resultado(self):
        m = mesa((1000,) * 6)
        while not m.terminada:
            copia, _ = self.copiar(m)
            self.comprobar_igual(m, copia)
            if m.turno is None:
                m.avanzar_calle()
            else:
                m.actuar(m.turno, "call")
        registro = construir_registro(m, 3)
        copia, datos = self.copiar(m, True, registro)
        self.comprobar_igual(m, copia)
        self.assertEqual(m.pagos, copia.pagos)
        self.assertTrue(datos["registrada"])
        self.assertFalse(datos["ayudas"])

    def test_subida_pendiente_y_rng_se_conservan(self):
        m = mesa((1000,) * 6)
        m.actuar(3, "raise", 200)
        accion, total = m.decidir_bot()
        m.actuar(m.turno, accion, total)
        copia, _ = self.copiar(m)
        self.comprobar_igual(m, copia)
        self.assertEqual(m.decidir_bot(), copia.decidir_bot())

    def test_recuperacion_con_all_ins_botes_y_ciegas_cortas(self):
        for semilla in range(12):
            m = mesa((10, 30, 80, 130, 270, 700), semilla)
            while not m.terminada:
                copia, _ = self.copiar(m)
                self.comprobar_igual(m, copia)
                self.assertEqual(m.rng.getstate(), copia.rng.getstate())
                if m.turno is None:
                    m.avanzar_calle()
                else:
                    accion, total = m.decidir_bot()
                    m.actuar(m.turno, accion, total)
            copia, _ = self.copiar(m, False, construir_registro(m, 3))
            self.comprobar_igual(m, copia)
            self.assertEqual(m.pagos, copia.pagos)
            self.assertEqual(m.devoluciones, copia.devoluciones)
            self.assertEqual(sum(j.fichas for j in copia.jugadores), 1220)

    def test_all_in_y_hero_retirado(self):
        m = mesa((80, 100, 150, 200, 300, 400))
        m.actuar(3, "fold")
        m.actuar(4, "raise", 300)
        while m.turno is not None:
            m.actuar(m.turno, "call")
        m.avanzar_calle()
        copia, _ = self.copiar(m)
        self.comprobar_igual(m, copia)
        self.assertTrue(copia.jugadores[3].retirado)

    def test_resultado_pendiente_no_duplica_historial(self):
        m = mesa((1000,) * 6)
        while not m.terminada:
            m.actuar(m.turno, "fold")
        registro = construir_registro(m, 3)
        _, datos = self.copiar(m, False, registro)
        with tempfile.TemporaryDirectory() as directorio:
            bd = BaseDatosLocal(str(Path(directorio) / "historial.json"))
            bd.registrar_mano(registro)
            self.assertFalse(bd.registrar_mano(datos["pendiente"]))
            self.assertEqual(bd.cargar_historial()["manos_totales"], 1)

    def test_accion_alterada_rechazada(self):
        m = mesa((1000,) * 6)
        m.actuar(3, "call")
        _, datos = self.copiar(m)
        datos["acciones"][0]["cantidad"] = 900
        with self.assertRaises(ValueError):
            recuperar(datos)

    def test_escritura_atomica_y_sesion_corrupta(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "sesion.json"
            archivo = ArchivoSesion(ruta)
            self.assertIsNone(archivo.cargar())
            datos = instantanea(mesa((1000,) * 6), False, True)
            archivo.guardar(datos)
            original = ruta.read_bytes()
            with patch("sesion_guardada.os.replace", side_effect=OSError("Sin espacio")):
                with self.assertRaises(ErrorSesion):
                    archivo.guardar(datos)
            self.assertEqual(ruta.read_bytes(), original)
            self.assertEqual(list(Path(directorio).glob("*.tmp")), [])
            self.assertEqual(archivo.cargar()[0].id_mano, datos["id"])
            ruta.write_text("{", encoding="utf-8")
            with self.assertRaises(ErrorSesion):
                archivo.cargar()
            self.assertEqual(ruta.read_text(), "{")
