"""Pruebas Qt sin ventana visible y con historial temporal."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QEventLoop, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTableWidget, QPlainTextEdit, QLabel
from persistencia import ErrorHistorial

from logica_poker import BaseDatosLocal
from main import VentanaMesaPoker
from componentes_visuales import obtener_ruta_imagen_carta


class InterfazTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.bd = BaseDatosLocal(str(Path(self.temporal.name) / "historial.json"))
        with patch("main.BaseDatosLocal", return_value=self.bd):
            self.ventana = VentanaMesaPoker()
        self.ventana.motor.rng = random.Random(19)
        self.ventana.tabs.setCurrentWidget(self.ventana.tab_mesa)
        self.ventana.show()
        self.app.processEvents()
        self.ventana.timer_bot.stop()

    def tearDown(self):
        self.ventana.timer_bot.stop()
        self.ventana.close()
        self.ventana.deleteLater()
        self.app.processEvents()
        self.temporal.cleanup()

    def test_call_no_salta_calle_y_controles_se_bloquean(self):
        v = self.ventana
        self.assertEqual(v.motor.turno, v.HEROE)
        self.assertTrue(v.btn_call.isEnabled())
        self.assertEqual(v.btn_call.text(), "Call 40")
        QTest.mouseClick(v.btn_call, Qt.MouseButton.LeftButton)
        v.timer_bot.stop()
        self.assertEqual(v.motor.jugadores[v.HEROE].fichas, 1960)
        self.assertEqual(v.motor.fase, 0)
        self.assertEqual(v.layout_centro.count(), 0)
        self.assertFalse(v.btn_call.isEnabled())
        self.assertFalse(v.btn_fold.isEnabled())

    def test_manos_completas_y_un_registro_por_mano(self):
        v = self.ventana
        total_inicial = self.bd.cargar_historial()["manos_totales"]
        for mano in range(6):
            if mano:
                v.iniciar_nueva_mano()
                v.timer_bot.stop()
            pasos = 0
            while not v.motor.terminada:
                if v.motor.turno is None:
                    v._avanzar_calle_automatica()
                elif v.motor.turno == v.HEROE:
                    v.avanzar_fase_juego()
                else:
                    v._accion_bot()
                v.timer_bot.stop()
                self.app.processEvents()
                pasos += 1
                self.assertLess(pasos, 200)
                self.assertEqual(v.layout_centro.count(), len(v.motor.comunitarias))
                self.assertEqual(v.sesion.fichas_actuales, v.motor.jugadores[v.HEROE].fichas)
            v._refrescar_mesa()
            self.assertFalse(v.btn_fold.isEnabled())
            self.assertFalse(v.btn_raise.isEnabled())
            self.assertEqual(self.bd.cargar_historial()["manos_totales"], total_inicial + mano + 1)
            tablas = v.tab_historial.findChildren(QTableWidget, "tabla_historial")
            self.assertEqual(len(tablas), 1)
            self.assertEqual(tablas[0].rowCount(), mano + 1)

    def test_temporizador_ejecuta_turno_rival(self):
        v = self.ventana
        v.avanzar_fase_juego()
        self.assertTrue(v.timer_bot.isActive())
        QTest.qWait(550)
        v.timer_bot.stop()
        self.assertGreaterEqual(len(v.motor.eventos), 2)
        self.assertEqual(v.motor.eventos[1]["jugador"], 4)

    def test_menu_pausa_y_reanuda_la_mesa(self):
        v = self.ventana
        v.chk_ayudas.setChecked(False)
        v.avanzar_fase_juego()
        estado = (v.motor.id_mano, v.motor.turno, len(v.motor.eventos))
        v.tabs.setCurrentWidget(v.tab_inicio)
        self.assertFalse(v.timer_bot.isActive())
        self.assertFalse(v.timer_calle.isActive())
        QTest.qWait(500)
        self.assertEqual(estado, (v.motor.id_mano, v.motor.turno, len(v.motor.eventos)))
        v.tabs.setCurrentWidget(v.tab_mesa)
        self.assertTrue(v.timer_bot.isActive())
        v.timer_bot.stop()

    def test_fold_no_registra_dos_veces(self):
        v = self.ventana
        total = self.bd.cargar_historial()["manos_totales"]
        v.ejecutar_fold()
        v.timer_bot.stop()
        self.assertFalse(v.btn_fold.isEnabled())
        while not v.motor.terminada:
            if v.motor.turno is None:
                v._avanzar_calle_automatica()
            else:
                v._accion_bot()
            v.timer_bot.stop()
        v._finalizar_mano()
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], total + 1)

    def test_reparto_automatico_espera_apuestas_y_no_admite_doble_avance(self):
        v = self.ventana
        v.chk_ayudas.setChecked(False)
        self.assertFalse(v.timer_calle.isActive())
        while v.motor.turno is not None:
            v.motor.actuar(v.motor.turno, "call")
        v.PAUSA_CALLE_MS = 20
        v._refrescar_mesa()
        self.assertFalse(v.btn_call.isEnabled())
        v.avanzar_fase_juego()
        self.assertEqual(v.motor.fase, 0)
        QTest.qWait(80)
        v.timer_bot.stop()
        self.assertEqual(len(v.motor.comunitarias), 3)
        self.assertFalse(v.timer_calle.isActive())
        v._avanzar_calle_automatica()
        self.assertEqual(v.motor.fase, 1)
        self.assertEqual(v.fichas_bote.cantidad, v.motor.bote)

    def test_all_in_reparte_todas_las_calles_y_registra_una_vez(self):
        v = self.ventana
        v.chk_ayudas.setChecked(False)
        m = v.motor
        while m.turno is not None:
            i = m.turno
            j = m.jugadores[i]
            if m.puede_subir(i) and j.apuesta + j.fichas > m.apuesta_actual:
                m.actuar(i, "raise", j.apuesta + j.fichas)
            else:
                m.actuar(i, "call")
        v.PAUSA_CALLE_MS = 20
        cartas = []
        v.timer_calle.timeout.connect(lambda: cartas.append(len(m.comunitarias)))
        v._refrescar_mesa()
        QTest.qWait(250)
        self.assertTrue(m.terminada)
        self.assertEqual(cartas, [3, 4, 5, 5])
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 1)
        self.assertFalse(v.timer_calle.isActive())
        self.assertEqual(v.fichas_bote.cantidad, 0)
        self.assertEqual(v.btn_call.text(), "Nueva sesión" if not m.jugadores[v.HEROE].fichas else "Siguiente mano")

    def test_fichas_visuales_crecen_con_limite(self):
        from componentes_dibujo import distribuir_fichas
        cantidades = [0, 20, 60, 200, 1000, 10000, 1000000]
        totales = []
        for cantidad in cantidades:
            pilas = distribuir_fichas(cantidad)
            self.assertLessEqual(len(pilas), 6)
            self.assertTrue(all(0 < altura <= 8 for altura in pilas))
            totales.append(sum(pilas))
        self.assertEqual(totales, sorted(totales))
        self.assertEqual(totales[0], 0)
        self.assertEqual(totales[-1], 48)

    def test_rutas_de_cartas_independientes_del_directorio(self):
        for j in self.ventana.motor.jugadores:
            for carta in j.cartas:
                ruta = Path(obtener_ruta_imagen_carta(carta))
                self.assertTrue(ruta.is_absolute())
                self.assertTrue(ruta.is_file())

    def test_historial_y_reintento_de_guardado(self):
        v = self.ventana
        while not v.motor.terminada:
            if v.motor.turno is None:
                v.motor.avanzar_calle()
            else:
                v.motor.actuar(v.motor.turno, "call")
        id_terminada = v.motor.id_mano
        with patch.object(self.bd, "registrar_mano", side_effect=ErrorHistorial("Disco lleno")):
            v._refrescar_mesa()
            self.assertFalse(v.mano_registrada)
            self.assertEqual(v.btn_call.text(), "Reintentar guardado")
            v.iniciar_nueva_mano()
            self.assertEqual(v.motor.id_mano, id_terminada)
        v._finalizar_mano()
        self.assertTrue(v.mano_registrada)
        tabla = v.tab_historial.findChild(QTableWidget, "tabla_historial")
        self.assertEqual(tabla.rowCount(), 1)
        detalle = v.tab_historial.findChild(QPlainTextEdit, "detalle_historial")
        self.assertIn(id_terminada, detalle.toPlainText())
        self.assertIn("PREFLOP", detalle.toPlainText())
        self.assertIn("RESULTADO", detalle.toPlainText())
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 1)
        v.iniciar_nueva_mano()
        v.timer_bot.stop()
        v.close()
        self.assertEqual(self.bd.cargar_historial()["manos_totales"], 1)

    def test_estadisticas_vacias_y_ayuda(self):
        v = self.ventana
        self.assertEqual(v.tab_stats.findChild(QLabel, "valor_VPIP").text(), "Sin datos")
        from ventana_ayuda import VentanaAyudaStats
        dialogo = VentanaAyudaStats("3-BET", {"casos": 1, "oportunidades": 3, "porcentaje": 100 / 3}, v)
        textos = " ".join(label.text() for label in dialogo.findChildren(QLabel))
        self.assertIn("33.3 %", textos)
        self.assertIn("oportunidades legales", textos)
        dialogo.close()

    def test_interruptor_ayudas_no_altera_la_mano(self):
        v = self.ventana
        self.assertIn("40.0 %", v.lbl_ayuda_call.text())
        estado = (v.motor.turno, v.motor.bote, v.motor.id_mano)
        v.chk_ayudas.setChecked(False)
        self.assertTrue(v.panel_ayudas.isHidden())
        self.assertTrue(v.lbl_hud_equity.isHidden())
        v.chk_ayudas.setChecked(True)
        self.assertFalse(v.panel_ayudas.isHidden())
        self.assertFalse(v.lbl_hud_equity.isHidden())
        self.assertEqual(estado, (v.motor.turno, v.motor.bote, v.motor.id_mano))

    def test_reabrir_recupera_mano_fichas_y_ayudas(self):
        v = self.ventana
        v.avanzar_fase_juego()
        v.timer_bot.stop()
        v.chk_ayudas.setChecked(False)
        estado = (v.motor.id_mano, v.motor.bote, v.motor.turno,
                  [j.fichas for j in v.motor.jugadores])
        v.close()
        with patch("main.BaseDatosLocal", return_value=self.bd):
            recuperada = VentanaMesaPoker()
        recuperada.timer_bot.stop()
        try:
            self.assertEqual(estado, (recuperada.motor.id_mano, recuperada.motor.bote,
                                     recuperada.motor.turno, [j.fichas for j in recuperada.motor.jugadores]))
            self.assertFalse(recuperada.chk_ayudas.isChecked())
            self.assertEqual(self.bd.cargar_historial()["manos_totales"], 0)
        finally:
            recuperada.close()
            recuperada.deleteLater()

    def test_equity_descarta_resultado_de_otra_mano(self):
        v = self.ventana
        clave = v.clave_equity
        dato = {"porcentaje": 35, "rivales": 5, "muestras": 600, "margen": 4}
        v._recibir_equity(("otra_mano", *clave[1:]), dato)
        self.assertNotIn("35.0", v.lbl_equity_estimada.text())
        v._recibir_equity(clave, dato)
        self.assertIn("35.0", v.lbl_equity_estimada.text())
        v.chk_ayudas.setChecked(False)
        v._recibir_equity(clave, dato)
        self.assertEqual(v.lbl_equity_estimada.text(), "")

    def test_equity_en_segundo_plano_llega_a_la_ventana(self):
        v = self.ventana
        bucle = QEventLoop()
        tiempo = QTimer()
        tiempo.setSingleShot(True)
        tiempo.timeout.connect(bucle.quit)
        v.servicio_equity.resultado.connect(bucle.quit)
        if "simulaciones" not in v.lbl_equity_estimada.text():
            tiempo.start(8000)
            bucle.exec()
        tiempo.stop()
        v.servicio_equity.resultado.disconnect(bucle.quit)
        self.assertIn("600 simulaciones", v.lbl_equity_estimada.text())
        self.assertIn("aleatorios", v.lbl_equity_estimada.text())


if __name__ == "__main__":
    unittest.main()
