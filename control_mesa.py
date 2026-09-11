"""Conexión entre los controles Qt y el motor de la mesa."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QMessageBox

import componentes_visuales as cv
from logica_poker import EvaluadorManos
from motor_mesa import JugadorMesa, MotorMesa
from estadisticas import construir_registro
from persistencia import ErrorHistorial
from ayudas_poker import proyectos_visibles, referencia_call
from estrategia_bots import PERFILES
from sesion_guardada import instantanea, ErrorSesion


class ControlMesa:
    HEROE = 3
    ASIENTOS_BOTS = (0, 1, 2, 4, 5)
    FICHAS_INICIALES = (7100, 9921, 10884, 2000, 2850, 10176)
    PAUSA_CALLE_MS = 850

    def _crear_motor(self):
        nombres = [r["nombre"] for r in self.datos_rivales]
        nombres.insert(self.HEROE, self.jugador.nombre)
        self.motor = MotorMesa([JugadorMesa(n, f) for n, f in zip(nombres, self.FICHAS_INICIALES)])
        for asiento, perfil in zip(self.ASIENTOS_BOTS, ("conservador", "pagador", "agresivo", "equilibrado", "agresivo")):
            self.motor.jugadores[asiento].perfil = perfil
        if not hasattr(self, "timer_bot"):
            self.timer_bot = QTimer(self)
            self.timer_bot.setSingleShot(True)
            self.timer_bot.timeout.connect(self._accion_bot)
            self.timer_calle = QTimer(self)
            self.timer_calle.setSingleShot(True)
            self.timer_calle.timeout.connect(self._avanzar_calle_automatica)
            self.transicion_calle = None
        self.lbl_resultado_mano.setFixedSize(500, 70)
        self.lbl_resultado_mano.move(250, 310)
        self.lbl_resultado_mano.setWordWrap(True)
        self.lbl_resultado_mano.setStyleSheet("color: #00ffcc; background: rgba(10,30,15,210); border-radius: 4px;")

    def iniciar_nueva_mano(self):
        if not hasattr(self, "motor"):
            self._crear_motor()
            try:
                recuperada = self.archivo_sesion.cargar()
            except ErrorSesion as error:
                self.sesion_bloqueada = True
                self.statusBar().showMessage(f"{error} Archivo conservado; guardado de sesión desactivado.")
                recuperada = None
            if recuperada is not None:
                self.motor, datos = recuperada
                self.mano_registrada = datos["registrada"]
                if datos.get("pendiente"):
                    self.registro_pendiente = datos["pendiente"]
                self.chk_ayudas.blockSignals(True)
                self.chk_ayudas.setChecked(datos["ayudas"])
                self.chk_ayudas.blockSignals(False)
                self._mostrar_mano_propia()
                self._refrescar_mesa()
                self.statusBar().showMessage("Sesión recuperada: puedes continuar la mano.", 6000)
                return
        if not self.motor.terminada:
            return
        if hasattr(self, "mano_registrada") and not self.mano_registrada:
            self._finalizar_mano()
            if not self.mano_registrada:
                return
        if self.motor.jugadores[self.HEROE].fichas == 0 or sum(j.fichas > 0 for j in self.motor.jugadores) < 2:
            self._crear_motor()
        self.motor.iniciar_mano()
        self.mano_registrada = False
        self.lbl_resultado_mano.hide()
        self._mostrar_mano_propia()
        self._refrescar_mesa()

    def _mostrar_mano_propia(self):
        self.mis_cartas_actuales = self.motor.jugadores[self.HEROE].cartas
        cv.limpiar_layout(self.layout_mano)
        self._mostrar_cartas(self.layout_mano, self.mis_cartas_actuales, 75, 105)

    def _guardar_sesion(self):
        if not hasattr(self, "motor") or not hasattr(self.motor, "id_mano"):
            return True
        if self.sesion_bloqueada:
            return False
        pendiente = getattr(self, "registro_pendiente", None)
        if pendiente is not None and pendiente["id"] != self.motor.id_mano:
            pendiente = None
        try:
            datos = instantanea(self.motor, self.mano_registrada, self.chk_ayudas.isChecked(), pendiente)
            self.archivo_sesion.guardar(datos)
        except ErrorSesion as error:
            self.statusBar().showMessage(str(error))
            return False
        return True

    def _mostrar_cartas(self, layout, cartas, ancho, alto):
        for carta in cartas:
            lbl = QLabel()
            pix = QPixmap(cv.obtener_ruta_imagen_carta(carta))
            lbl.setPixmap(pix.scaled(ancho, alto, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(lbl)

    def _refrescar_mesa(self):
        m = self.motor
        self.timer_bot.stop()
        self.timer_calle.stop()
        self.transicion_calle = None
        if m.terminada and not self.mano_registrada and (
                not hasattr(self, "registro_pendiente") or self.registro_pendiente["id"] != m.id_mano):
            self.registro_pendiente = construir_registro(m, self.HEROE)
        # Guardar el resultado pendiente antes de escribir el historial permite
        # reintentar una finalización tras un cierre inesperado sin duplicarla.
        self._guardar_sesion()
        h = m.jugadores[self.HEROE]
        self.sesion.fichas_actuales = h.fichas
        self.fase_actual = m.fase
        self.bote_actual = m.bote
        self.apuesta_a_pagar = m.por_pagar(self.HEROE) if not m.terminada else 0
        self.lbl_bote.setText(f"{m.CALLES[m.fase]} · BOTE: {m.bote:,}")
        self.fichas_bote.actualizar_bote(m.bote)
        self.lbl_nombre_propio.setText(f"[{h.posicion}] {h.nombre} (Tú)")
        self.lbl_fichas_propias.setText(f"{h.fichas:,}")
        self._actualizar_asiento(self.HEROE, self.panel_mio, self.lbl_apuesta_propia)
        cv.limpiar_layout(self.layout_centro)
        self._mostrar_cartas(self.layout_centro, m.comunitarias, 65, 95)
        for visual, asiento in enumerate(self.ASIENTOS_BOTS):
            j = m.jugadores[asiento]
            perfil = self.asientos_visuales[visual]
            perfil["nombre"].setText(f"[{j.posicion}] {j.nombre}")
            estilo = PERFILES[j.perfil]
            perfil["nombre"].setToolTip(f"{estilo.nombre}: {estilo.descripcion}")
            perfil["fichas"].setText(f"{j.fichas:,}")
            color = "#666666" if j.retirado or not j.participando else ("#ffd700" if m.turno == asiento else "#00ffcc")
            perfil["nombre"].setStyleSheet(f"color: {color}; border: none; background: transparent;")
            etiqueta = self.lbl_apuestas_bots[visual]
            self._actualizar_asiento(asiento, perfil["panel"], etiqueta)
            for lbl, carta in zip(perfil.get("cartas", []), j.cartas):
                ruta = cv.obtener_ruta_imagen_carta(carta) if m.terminada and m.showdown and not j.retirado else cv.ruta_reverso()
                lbl.setPixmap(QPixmap(ruta).scaled(40, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl.setVisible(j.participando and not j.retirado)
            if not j.participando:
                for lbl in perfil.get("cartas", []):
                    lbl.hide()
        self.actualizar_analisis_mano_ia()
        self.configurar_limites_slider()
        self.actualizar_textos_botones_accion()
        if m.terminada:
            self._finalizar_mano()
            self._guardar_sesion()
        elif m.turno is not None and m.turno != self.HEROE:
            self.lbl_hud_consejo.setText(f"Turno de {m.jugadores[m.turno].nombre}…")
            if self.tabs.currentWidget() is self.tab_mesa:
                self.timer_bot.start(450)
        elif m.turno == self.HEROE:
            deuda = min(m.por_pagar(self.HEROE), h.fichas)
            self.lbl_hud_consejo.setText(f"Tu turno · Aportado en esta calle: {h.apuesta}. " +
                                       (f"Igualar cuesta {deuda} fichas." if deuda else "Puedes pasar o apostar."))
        else:
            siguiente = "el resultado" if m.fase == 3 else m.CALLES[m.fase + 1]
            self.lbl_hud_consejo.setText(f"Apuestas cerradas. Mostrando {siguiente}…")
            self.transicion_calle = (m.id_mano, m.fase)
            if self.tabs.currentWidget() is self.tab_mesa:
                self.timer_calle.start(self.PAUSA_CALLE_MS)

    def _actualizar_asiento(self, asiento, panel, etiqueta):
        m = self.motor
        j = m.jugadores[asiento]
        activo = not m.terminada and m.turno == asiento
        color = "#ffd700" if activo else "#555555"
        panel.setStyleSheet(f"background-color: rgba(30,30,30,230); border: 2px solid {color}; border-radius: 8px; padding: 5px;")
        estado = ("TU TURNO" if asiento == self.HEROE else "SU TURNO") if activo else j.accion
        if m.terminada:
            estado = "Mano terminada"
        importe = 0 if m.terminada else j.apuesta
        etiqueta.setText(f"{estado or 'Esperando'}\nEn esta calle: {importe:,}")
        etiqueta.setToolTip("Total aportado en la ronda de apuestas actual. Ya está incluido en el bote.\nÚltima acción: " + (j.accion or "Ninguna"))
        etiqueta.setStyleSheet(f"color: {'#ffd700' if activo else '#dddddd'}; background-color: rgba(15,15,15,220); border: 1px solid {color}; border-radius: 4px; font: 11px 'Segoe UI';")
        etiqueta.setVisible(j.participando)

    def _avanzar_calle_automatica(self):
        m = self.motor
        if m.terminada or m.turno is not None or self.transicion_calle != (m.id_mano, m.fase):
            return
        self.timer_calle.stop()
        self.transicion_calle = None
        m.avanzar_calle()
        self._refrescar_mesa()

    def configurar_limites_slider(self):
        if not hasattr(self, "motor"):
            return
        h = self.motor.jugadores[self.HEROE]
        maximo = h.apuesta + h.fichas
        minimo = min(self.motor.minimo_subida(), maximo)
        self.slider_apuestas.blockSignals(True)
        self.slider_apuestas.setRange(minimo, maximo)
        self.slider_apuestas.setSingleStep(1)
        self.slider_apuestas.setValue(minimo)
        self.slider_apuestas.blockSignals(False)
        self.cantidad_a_apostar = minimo

    def actualizar_valor_slider(self, valor):
        self.cantidad_a_apostar = valor
        if hasattr(self, "motor"):
            self._texto_subida()

    def _texto_subida(self):
        h = self.motor.jugadores[self.HEROE]
        all_in = " · All-in" if self.cantidad_a_apostar == h.apuesta + h.fichas else ""
        verbo = "Subir a" if self.motor.apuesta_actual else "Apostar"
        self.btn_raise.setText(f"{verbo} {self.cantidad_a_apostar}{all_in}")

    def fijar_tamano_apuesta(self, tipo):
        m = self.motor
        h = m.jugadores[self.HEROE]
        # Raise del bote: pagar primero y subir el tamaño del bote resultante.
        base = m.apuesta_actual
        bote_tras_call = m.bote + m.por_pagar(self.HEROE)
        valores = {"min": self.slider_apuestas.minimum(), "max": h.apuesta + h.fichas,
                   "half": base + bote_tras_call // 2, "pot": base + bote_tras_call}
        self.slider_apuestas.setValue(max(self.slider_apuestas.minimum(), min(valores[tipo], self.slider_apuestas.maximum())))

    def actualizar_textos_botones_accion(self):
        m = self.motor
        h = m.jugadores[self.HEROE]
        propio = not m.terminada and m.turno == self.HEROE
        subir = propio and m.puede_subir(self.HEROE)
        self.btn_fold.setEnabled(propio)
        self.btn_fold.setText("Fold")
        for control in [self.btn_raise, self.slider_apuestas, self.btn_min, self.btn_half, self.btn_pot, self.btn_max]:
            control.setEnabled(subir)
        self.btn_call.setEnabled(m.terminada or propio)
        if m.terminada:
            reiniciar = h.fichas == 0 or sum(j.fichas > 0 for j in m.jugadores) < 2
            self.btn_call.setText("Nueva sesión" if reiniciar else "Siguiente mano")
        elif m.turno is None:
            self.btn_call.setText("Resolviendo…" if m.fase == 3 else "Repartiendo…")
        elif propio:
            deuda = min(m.por_pagar(self.HEROE), h.fichas)
            self.btn_call.setText(f"Call {deuda}" + (" · All-in" if deuda == h.fichas else "") if deuda else "Check")
        else:
            self.btn_call.setText("Turno rival…")
        self._texto_subida()

    def _actuar_usuario(self, accion, total=None):
        try:
            self.motor.actuar(self.HEROE, accion, total)
        except ValueError as error:
            QMessageBox.information(self, "Acción no disponible", str(error))
            return
        self._refrescar_mesa()

    def ejecutar_fold(self):
        self._actuar_usuario("fold")

    def ejecutar_apuesta_raise(self):
        self._actuar_usuario("raise", self.cantidad_a_apostar)

    def avanzar_fase_juego(self):
        if self.motor.terminada:
            self.iniciar_nueva_mano()
        elif self.motor.turno == self.HEROE:
            self._actuar_usuario("call" if self.motor.por_pagar(self.HEROE) else "check")

    def _accion_bot(self):
        if self.motor.terminada or self.motor.turno in (None, self.HEROE):
            return
        accion, total = self.motor.decidir_bot()
        self.motor.actuar(self.motor.turno, accion, total)
        self._refrescar_mesa()

    def actualizar_analisis_mano_ia(self):
        h = self.motor.jugadores[self.HEROE]
        self.lbl_hud_posicion.setText(f"POSICIÓN: {h.posicion} · {self.motor.CALLES[self.motor.fase]}")
        self.lbl_hud_equity.setWordWrap(True)
        jugada = "Retirado" if h.retirado else EvaluadorManos().evaluar_mano(h.cartas, self.motor.comunitarias)
        self.lbl_hud_equity.setText(f"JUGADA: {jugada}")
        self.actualizar_ayudas()

    def actualizar_ayudas(self, _activadas=None):
        activadas = self.chk_ayudas.isChecked()
        self.panel_ayudas.setVisible(activadas)
        self.lbl_hud_equity.setVisible(activadas)
        if not hasattr(self, "motor"):
            return
        m = self.motor
        h = m.jugadores[self.HEROE]
        self._actualizar_equity()
        self.lbl_ayuda_call.setToolTip("")
        if m.terminada or h.retirado:
            self.lbl_ayuda_call.setText("Mano terminada" if m.terminada else "Te has retirado")
            self.lbl_ayuda_proyectos.setText("Sin decisiones pendientes para ti.")
            self.lbl_ayuda_nota.setText("")
            return
        proyectos = proyectos_visibles(h.cartas, m.comunitarias)
        if proyectos:
            texto = "Proyectos: " + " · ".join(proyectos)
        elif m.fase == 0:
            texto = "Los proyectos se analizan a partir del flop."
        elif m.fase == 3:
            texto = "River: no quedan cartas por salir."
        else:
            texto = "Sin proyecto de color o escalera a una carta."
        self.lbl_ayuda_proyectos.setText(texto)
        self.lbl_ayuda_proyectos.setToolTip("Solo proyectos que se completan con una carta; no incluye backdoors. Completar un proyecto no garantiza ganar. Los proyectos de la mesa también pueden beneficiar a tus rivales.")
        self.lbl_ayuda_nota.setText("Completar un proyecto no garantiza ganar.")
        if m.turno != self.HEROE:
            self.lbl_ayuda_call.setText("Esperando tu turno" if m.turno is not None else "Ronda de apuestas cerrada")
            return
        coste = min(m.por_pagar(self.HEROE), h.fichas)
        if not coste:
            self.lbl_ayuda_call.setText("Puedes pasar sin pagar · Check: 0 fichas")
            return
        dato = referencia_call(coste, [j.aportado for j in m.jugadores], self.HEROE)
        if dato["porcentaje"] is None:
            self.lbl_ayuda_call.setText(f"Pagar: {coste} · Parte del pago quedaría sin igualar")
        else:
            titulo = "Referencia" if dato["botes_limitados"] else "Equity mínima orientativa"
            self.lbl_ayuda_call.setText(f"Pagar: {coste} · {titulo}: {dato['porcentaje']:.1f} %")
        self.lbl_ayuda_call.setToolTip(f"Coste de pagar / bote disputable tras pagar × 100.\n{coste} / {dato['bote_elegible']} × 100.\nNo estima la equity de tus cartas. Es una referencia sin apuestas futuras ni aportaciones posteriores de otros jugadores. En botes secundarios importa la cuota esperada de cada bote elegible.")
        self.lbl_ayuda_nota.setText("Botes secundarios: referencia limitada a tu aportación." if dato["botes_limitados"] else "Umbral del pago, no equity de tu mano. Sin apuestas futuras.")

    def _actualizar_equity(self):
        m = self.motor
        h = m.jugadores[self.HEROE]
        if not self.chk_ayudas.isChecked() or m.terminada or h.retirado:
            self.servicio_equity.cancelar()
            self.clave_equity = None
            self.lbl_equity_estimada.clear()
            return
        convertir = lambda cartas: tuple(sorted((c.valor_num, c.palo_num) for c in cartas))
        clave = (m.id_mano, convertir(h.cartas), convertir(m.comunitarias), len(m.vivos()) - 1)
        if getattr(self, "clave_equity", None) == clave:
            return
        self.clave_equity = clave
        self.lbl_equity_estimada.setText("Equity: calculando frente a manos aleatorias…")
        self.lbl_equity_estimada.setToolTip("Cuota media de un bote común al showdown, incluyendo empates. Los rivales se simulan con manos aleatorias: no usa sus cartas reales ni infiere sus rangos por sus apuestas. El margen es una cota conservadora al 95 % del error de simulación, dentro de ese modelo, limitada al rango 0–100 %. No se aplica directamente a botes secundarios ni garantiza que pagar sea rentable.")
        self.servicio_equity.solicitar(clave)

    def _recibir_equity(self, clave, resultado):
        if clave != getattr(self, "clave_equity", None) or not self.chk_ayudas.isChecked():
            return
        if "error" in resultado:
            self.lbl_equity_estimada.setText(resultado["error"])
            return
        self.lbl_equity_estimada.setText(
            f"Equity ≈ {resultado['porcentaje']:.1f} % vs {resultado['rivales']} rival(es) aleatorios\n"
            f"{resultado['muestras']} simulaciones · margen conservador ±{resultado['margen']:.1f} puntos")

    def _finalizar_mano(self):
        m = self.motor
        h = m.jugadores[self.HEROE]
        premios = [f"{m.jugadores[i].nombre}: {cantidad:,}" for i, cantidad in m.pagos.items()]
        texto = "Reparto del bote · " + " | ".join(premios)
        if m.devoluciones:
            texto += "\nSin igualar, devuelto: " + ", ".join(f"{m.jugadores[i].nombre} {v:,}" for i, v in m.devoluciones.items())
        self.lbl_resultado_mano.setText(texto)
        self.lbl_resultado_mano.setToolTip("\n".join(
            f"{m.jugadores[i].nombre}: {EvaluadorManos().evaluar_mano(m.jugadores[i].cartas, m.comunitarias)}"
            for i in m.vivos()) if m.showdown else "Los demás jugadores se retiraron.")
        self.lbl_resultado_mano.show()
        self.lbl_hud_consejo.setText("Mano terminada. Las cartas rivales se muestran si llegaron al showdown." +
                                   (" Sin fichas: puedes iniciar una nueva sesión de práctica." if not h.fichas else ""))
        if self.mano_registrada:
            return
        if not hasattr(self, "registro_pendiente") or self.registro_pendiente["id"] != m.id_mano:
            self.registro_pendiente = construir_registro(m, self.HEROE)
        try:
            self.bd_local.registrar_mano(self.registro_pendiente)
        except ErrorHistorial as error:
            self.lbl_hud_consejo.setText(str(error))
            self.btn_call.setText("Reintentar guardado")
            return
        self.mano_registrada = True
        self.init_stats_ui()
