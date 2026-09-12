"""Control de la mesa compartida para estados recibidos del servidor."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from construccion_mesa import ConstruccionMesa
from presentacion_mesa import PresentacionMesa, POSICIONES_RIVALES, convertir_carta
from componentes_dibujo import MesaDibujo
from logica_poker import EvaluadorManos
from ayudas_poker import proyectos_visibles, referencia_call
from equity import ServicioEquity


class VistaMesaRed(ConstruccionMesa, PresentacionMesa, QWidget):
    accion = Signal(str, int)
    nueva_mano = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado = None
        self.puede_iniciar = False
        self.clave_equity = None
        self.asientos_visuales = {}
        self.cantidad_a_apostar = 0
        self.datos_rivales = [{'nombre': '', 'fichas': '', 'x': x, 'y': y} for x, y in POSICIONES_RIVALES]
        self.servicio_equity = ServicioEquity(self)
        self.servicio_equity.resultado.connect(self._recibir_equity)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tab_mesa = MesaDibujo()
        layout.addWidget(self.tab_mesa)
        self.setMinimumSize(1000, 690)
        self.init_ui()
        self.construir_asientos()
        # Alias de controles públicos empleados por las pruebas de transporte.
        self.fold, self.call, self.raise_ = self.btn_fold, self.btn_call, self.btn_raise
        self.total = self.slider_apuestas
        self.bloquear()

    def bloquear(self):
        for widget in (self.btn_fold, self.btn_call, self.btn_raise, self.slider_apuestas,
                       self.btn_min, self.btn_half, self.btn_pot, self.btn_max):
            widget.setEnabled(False)

    def mostrar(self, estado, puede_iniciar=False):
        self.estado = estado
        self.puede_iniciar = puede_iniciar
        self.pintar_estado(estado)
        c = estado['controles']
        self.slider_apuestas.blockSignals(True)
        self.slider_apuestas.setRange(c['minimo'], c['maximo'])
        self.slider_apuestas.setValue(c['minimo'])
        self.slider_apuestas.blockSignals(False)
        self.actualizar_valor_slider(c['minimo'])
        self.btn_fold.setEnabled(c['actuar'])
        self.btn_call.setEnabled(c['actuar'] or (estado['terminada'] and puede_iniciar))
        for widget in (self.btn_raise, self.slider_apuestas, self.btn_min, self.btn_half, self.btn_pot, self.btn_max):
            widget.setEnabled(c['subir'])
        h = estado['jugadores'][estado['tu_asiento']]
        self.lbl_hud_posicion.setText(f"POSICIÓN: {h['posicion']} · {estado['fase']}")
        if estado['terminada']:
            self.btn_call.setText('Siguiente mano' if puede_iniciar else 'Esperando al anfitrión')
            self.lbl_hud_consejo.setText('Mano terminada. El anfitrión inicia la siguiente.' if puede_iniciar or sum(j['fichas'] > 0 for j in estado['jugadores']) >= 2 else 'Fin de la sesión. Crea otra sala para volver a jugar.')
            reparto = 'Reparto del bote · ' + ' | '.join(f"{estado['jugadores'][p['asiento']]['nombre']}: {p['cantidad']:,}" for p in estado['pagos'])
            if estado['devoluciones']:
                reparto += '\nSin igualar, devuelto: ' + ', '.join(f"{estado['jugadores'][p['asiento']]['nombre']} {p['cantidad']:,}" for p in estado['devoluciones'])
            self.lbl_resultado_mano.setText(reparto)
            self.lbl_resultado_mano.show()
        else:
            self.lbl_resultado_mano.hide()
            if c['actuar']:
                self.btn_call.setText(f"Call {c['pagar']}" + (' · All-in' if c['pagar'] == h['fichas'] else '') if c['pagar'] else 'Check')
                self.lbl_hud_consejo.setText(f"Tu turno · Aportado en esta calle: {h['apuesta']}. " + (f"Igualar cuesta {c['pagar']} fichas." if c['pagar'] else 'Puedes pasar o apostar.'))
            else:
                self.btn_call.setText('Repartiendo…' if estado['turno'] is None else 'Turno rival…')
                self.lbl_hud_consejo.setText('Apuestas cerradas. Repartiendo…' if estado['turno'] is None else f"Turno de {estado['jugadores'][estado['turno']]['nombre']}…")
        self.actualizar_ayudas()

    def actualizar_valor_slider(self, valor):
        self.cantidad_a_apostar = valor
        if not self.estado:
            return
        c = self.estado['controles']
        verbo = 'Subir a' if self.estado['apuesta_actual'] else 'Apostar'
        self.btn_raise.setText(f"{verbo} {valor}" + (' · All-in' if valor == c['maximo'] else ''))

    def fijar_tamano_apuesta(self, tipo):
        if not self.estado:
            return
        e = self.estado
        c = e['controles']
        bote = e['bote'] + c['pagar']
        valores = {'min': c['minimo'], 'max': c['maximo'],
                   'half': e['apuesta_actual'] + bote // 2, 'pot': e['apuesta_actual'] + bote}
        self.slider_apuestas.setValue(max(c['minimo'], min(c['maximo'], valores[tipo])))

    def ejecutar_fold(self):
        self.accion.emit('fold', 0)

    def ejecutar_apuesta_raise(self):
        self.accion.emit('raise', self.cantidad_a_apostar)

    def avanzar_fase_juego(self):
        if self.estado and self.estado['terminada']:
            if self.puede_iniciar:
                self.nueva_mano.emit()
        else:
            self.accion.emit('call', 0)

    def _guardar_sesion(self):
        # La vista remota no guarda el motor ni el historial de práctica.
        return True

    def actualizar_ayudas(self, _activadas=None):
        activadas = self.chk_ayudas.isChecked()
        self.panel_ayudas.setVisible(activadas)
        self.lbl_hud_equity.setVisible(activadas)
        if not self.estado:
            return
        e = self.estado
        h = e['jugadores'][e['tu_asiento']]
        mano = [convertir_carta(c) for c in h['cartas'] if c is not None]
        mesa = [convertir_carta(c) for c in e['mesa']]
        jugada = 'Retirado' if h['retirado'] else EvaluadorManos().evaluar_mano(mano, mesa)
        self.lbl_hud_equity.setWordWrap(True)
        self.lbl_hud_equity.setText('JUGADA: ' + jugada)
        for label in (self.lbl_ayuda_call, self.lbl_ayuda_proyectos, self.lbl_ayuda_nota):
            label.clear()
        if not activadas or e['terminada'] or h['retirado'] or not h['participando']:
            self.servicio_equity.cancelar()
            self.clave_equity = None
            self.lbl_equity_estimada.clear()
            self.lbl_ayuda_call.setText('Mano terminada' if e['terminada'] else 'Sin decisiones pendientes')
            return
        convertir = lambda cartas: tuple(sorted((c.valor_num, c.palo_num) for c in cartas))
        rivales = sum(j['participando'] and not j['retirado'] for j in e['jugadores']) - 1
        clave = (e['id_mano'], convertir(mano), convertir(mesa), rivales)
        if self.clave_equity != clave:
            self.clave_equity = clave
            self.lbl_equity_estimada.setText('Equity: calculando frente a manos aleatorias…')
            self.servicio_equity.solicitar(clave)
        proyectos = proyectos_visibles(mano, mesa)
        self.lbl_ayuda_proyectos.setText('Proyectos: ' + ' · '.join(proyectos) if proyectos else 'River: no quedan cartas por salir.' if len(mesa) == 5 else 'Sin proyecto a una carta.' if mesa else 'Los proyectos se analizan a partir del flop.')
        c = e['controles']
        if not c['actuar']:
            self.lbl_ayuda_call.setText('Esperando tu turno')
        elif not c['pagar']:
            self.lbl_ayuda_call.setText('Puedes pasar sin pagar · Check: 0 fichas')
        else:
            dato = referencia_call(c['pagar'], [j['aportado'] for j in e['jugadores']], e['tu_asiento'])
            self.lbl_ayuda_call.setText(f"Pagar: {c['pagar']} · Referencia: {dato['porcentaje']:.1f} %" if dato['porcentaje'] is not None else f"Pagar: {c['pagar']} · Parte del pago quedaría sin igualar")
        self.lbl_ayuda_nota.setText('Equity frente a manos aleatorias; no garantiza ganar.')
        self.lbl_equity_estimada.setToolTip('Simulación solo con tus cartas y la mesa. Rivales aleatorios, sin usar sus cartas ocultas. No se aplica directamente a botes secundarios.')

    def _recibir_equity(self, clave, resultado):
        if clave != self.clave_equity or not self.chk_ayudas.isChecked():
            return
        self.lbl_equity_estimada.setText(resultado['error'] if 'error' in resultado else
            f"Equity ≈ {resultado['porcentaje']:.1f} % vs {resultado['rivales']} rival(es) aleatorios\n"
            f"{resultado['muestras']} simulaciones · margen conservador ±{resultado['margen']:.1f} puntos")

    def cancelar(self):
        self.servicio_equity.cancelar()
        self.clave_equity = None
        self.estado = None
        self.bloquear()
