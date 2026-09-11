from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from estadisticas import construir_registro, calcular_estadisticas
from persistencia import BaseDatosLocal, ErrorHistorial
from test_motor import mesa, cartas


def completar(m):
    while not m.terminada:
        if m.turno is None:
            m.avanzar_calle()
        else:
            m.actuar(m.turno, "call" if m.por_pagar(m.turno) else "check")


def victoria_showdown():
    m = mesa()
    while m.fase < 3 or m.turno is not None:
        if m.turno is None:
            m.avanzar_calle()
        else:
            m.actuar(m.turno, "call" if m.por_pagar(m.turno) else "check")
    m.jugadores[0].cartas = cartas("As Ah")
    m.jugadores[1].cartas = cartas("Ks Kh")
    m.jugadores[2].cartas = cartas("Qs Qh")
    m.comunitarias = cartas("2s 3h 7d 8c 9s")
    m.avanzar_calle()
    return construir_registro(m, 0)


class EstadisticasTests(unittest.TestCase):
    def test_muestra_vacia_no_inventa_porcentajes(self):
        stats = calcular_estadisticas([])
        self.assertEqual(stats["manos"], 0)
        self.assertTrue(all(m["porcentaje"] is None for m in stats["metricas"].values()))

    def test_denominadores_flop_showdown_y_total(self):
        m = mesa()
        m.actuar(0, "fold")
        completar(m)
        retirada_pf = construir_registro(m, 0)
        m = mesa()
        while m.turno is not None:
            m.actuar(m.turno, "call")
        m.avanzar_calle()
        m.actuar(1, "raise", 40)
        m.actuar(2, "fold")
        m.actuar(0, "fold")
        retirada_flop = construir_registro(m, 0)
        stats = calcular_estadisticas([retirada_pf, retirada_flop, victoria_showdown()])
        esperados = {"VPIP": (2, 3), "PFR": (0, 3), "WTSD": (1, 2), "WSD": (1, 1),
                     "WWSF": (1, 2), "PF-FOLD": (1, 3), "FLOP-FOLD": (1, 1)}
        for clave, (n, d) in esperados.items():
            self.assertEqual(stats["metricas"][clave]["casos"], n, clave)
            self.assertEqual(stats["metricas"][clave]["oportunidades"], d, clave)
        self.assertIsNone(stats["metricas"]["TURN-FOLD"]["porcentaje"])

    def test_ciegas_y_walk_no_son_vpip(self):
        m = mesa()
        m.actuar(0, "fold")
        m.actuar(1, "fold")
        stats = calcular_estadisticas([construir_registro(m, 2)])
        self.assertEqual(stats["metricas"]["VPIP"]["porcentaje"], 0)
        self.assertIsNone(stats["metricas"]["WTSD"]["porcentaje"])

    def test_robo_y_limper_excluido(self):
        m = mesa()
        m.actuar(0, "raise", 80)
        m.actuar(1, "fold")
        m.actuar(2, "fold")
        stats = calcular_estadisticas([construir_registro(m, 0)])
        self.assertEqual(stats["metricas"]["ATS"]["porcentaje"], 100)
        m = mesa((1000,) * 6)
        m.actuar(3, "call")
        m.actuar(4, "fold")
        m.actuar(5, "raise", 80)
        completar(m)
        stats = calcular_estadisticas([construir_registro(m, 5)])
        self.assertIsNone(stats["metricas"]["ATS"]["porcentaje"])

    def test_3bet_oportunidades_y_no_4bet(self):
        manos = []
        for respuesta in ("call", "raise"):
            m = mesa()
            m.actuar(0, "raise", 80)
            m.actuar(1, respuesta, 160 if respuesta == "raise" else None)
            completar(m)
            manos.append(construir_registro(m, 1))
        stats = calcular_estadisticas(manos)
        self.assertEqual(stats["metricas"]["3-BET"]["porcentaje"], 50)
        m = mesa()
        m.actuar(0, "raise", 80)
        m.actuar(1, "raise", 160)
        m.actuar(2, "raise", 320)
        completar(m)
        self.assertIsNone(calcular_estadisticas([construir_registro(m, 2)])["metricas"]["3-BET"]["porcentaje"])
        self.assertEqual(calcular_estadisticas([construir_registro(m, 0)])["metricas"]["PFR"]["casos"], 1)

    def test_sin_fichas_para_resubir_no_hay_oportunidad(self):
        m = mesa((1000, 80, 1000))
        m.actuar(0, "raise", 100)
        m.actuar(1, "call")
        completar(m)
        stats = calcular_estadisticas([construir_registro(m, 1)])
        self.assertIsNone(stats["metricas"]["3-BET"]["porcentaje"])

    def test_empates_y_devoluciones(self):
        m = mesa()
        while m.fase < 3 or m.turno is not None:
            if m.turno is None:
                m.avanzar_calle()
            else:
                m.actuar(m.turno, "call")
        m.jugadores[0].cartas = cartas("2h 3h")
        m.jugadores[1].cartas = cartas("4h 5h")
        m.jugadores[2].cartas = cartas("6h 7h")
        m.comunitarias = cartas("As Ks Qs Js Ts")
        m.avanzar_calle()
        stats = calcular_estadisticas([construir_registro(m, 0)])
        self.assertEqual(stats["balance"], 0)
        self.assertEqual(stats["metricas"]["WSD"]["porcentaje"], 100)
        registro = victoria_showdown()
        # El rival perdedor no recibe ningún bote aunque haya devolución.
        registro["heroe"] = 1
        registro["jugadores"][1]["devuelto"] = 10
        stats = calcular_estadisticas([registro])
        self.assertEqual(stats["metricas"]["WSD"]["casos"], 0)

    def test_snapshot_no_cambia_al_iniciar_otra_mano(self):
        m = mesa()
        completar(m)
        registro = construir_registro(m, 0)
        copia = deepcopy(registro)
        m.iniciar_mano()
        m.actuar(m.turno, "fold")
        self.assertEqual(registro, copia)

    def test_fold_cuenta_decisiones_no_manos(self):
        m = mesa()
        while m.turno is not None:
            m.actuar(m.turno, "call")
        m.avanzar_calle()
        m.actuar(1, "raise", 40)
        m.actuar(2, "raise", 80)
        m.actuar(0, "call")
        m.actuar(1, "raise", 120)
        m.actuar(2, "call")
        m.actuar(0, "fold")
        completar(m)
        metrica = calcular_estadisticas([construir_registro(m, 0)])["metricas"]["FLOP-FOLD"]
        self.assertEqual(metrica["casos"], 1)
        self.assertEqual(metrica["oportunidades"], 2)
        self.assertEqual(metrica["porcentaje"], 50)


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.ruta = Path(self.temporal.name) / "historial.json"
        self.bd = BaseDatosLocal(str(self.ruta))

    def tearDown(self):
        self.temporal.cleanup()

    def test_nueva_base_empieza_en_cero(self):
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 0)
        self.assertFalse(self.ruta.exists())

    def test_migracion_preserva_bytes_y_separa_estadisticas(self):
        anterior = {"manos_totales": 3774, "veces_vpip": 1431, "campo_personal": "Conservar"}
        original = json.dumps(anterior, ensure_ascii=False).encode("utf-8")
        self.ruta.write_bytes(original)
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 0)
        self.assertEqual(self.ruta.read_bytes(), original)
        self.bd.registrar_mano(victoria_showdown())
        datos = self.bd.cargar_historial()
        self.assertEqual(datos["historial_anterior"], anterior)
        self.assertEqual(datos["manos_totales"], 1)
        self.assertEqual(self.ruta.with_name("historial.anterior.json").read_bytes(), original)
        self.assertEqual(calcular_estadisticas(datos["manos"])["metricas"]["VPIP"]["porcentaje"], 100)

    def test_recarga_y_reintento_no_duplican(self):
        mano = victoria_showdown()
        self.assertTrue(self.bd.registrar_mano(mano))
        bd = BaseDatosLocal(str(self.ruta))
        self.assertFalse(bd.registrar_mano(mano))
        self.assertEqual(bd.cargar_historial()["manos"], [mano])

    def test_archivo_corrupto_no_se_sobrescribe(self):
        self.ruta.write_text('{"manos":', encoding="utf-8")
        original = self.ruta.read_bytes()
        with self.assertRaises(ErrorHistorial):
            self.bd.registrar_mano(victoria_showdown())
        self.assertEqual(self.ruta.read_bytes(), original)

    def test_error_de_escritura_deja_historial_y_permite_reintento(self):
        self.bd.registrar_mano(victoria_showdown())
        original = self.ruta.read_bytes()
        segunda = victoria_showdown()
        with patch("persistencia.os.replace", side_effect=OSError("Disco no disponible")):
            with self.assertRaises(ErrorHistorial):
                self.bd.registrar_mano(segunda)
        self.assertEqual(self.ruta.read_bytes(), original)
        self.assertEqual(list(self.ruta.parent.glob("*.tmp")), [])
        self.bd.registrar_mano(segunda)
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 2)

    def test_version_futura_no_se_sobrescribe(self):
        self.ruta.write_text('{"version": 99, "manos": []}', encoding="utf-8")
        original = self.ruta.read_bytes()
        with self.assertRaises(ErrorHistorial):
            self.bd.registrar_mano(victoria_showdown())
        self.assertEqual(self.ruta.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
