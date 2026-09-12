import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import unittest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtTest import QTest
from servidor_local import ServidorLocal
from interfaz_online import PanelOnline


class OnlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def esperar(self, condicion):
        for _ in range(300):
            if condicion():
                return
            QTest.qWait(10)
        self.fail('No llegó el estado esperado del servidor local')

    def setUp(self):
        self.servidor = ServidorLocal(0, pausa_ms=5)
        self.clientes = []
        self.mensajes = [[], []]
        self.estados = [None, None]
        for i in range(2):
            socket = QWebSocket()
            socket.textMessageReceived.connect(lambda t, i=i: self.recibir(i, t))
            self.clientes.append(socket)
            socket.open(QUrl(f'ws://127.0.0.1:{self.servidor.puerto}'))
        self.esperar(lambda: all(c.isValid() for c in self.clientes))
        self.enviar(0, tipo='crear', nombre='Uno')
        self.esperar(lambda: self.estados[0] is not None)
        self.enviar(1, tipo='unir', nombre='Dos', codigo=self.estados[0]['codigo'])
        self.esperar(lambda: self.estados[1] is not None and len(self.estados[0]['nombres']) == 2)

    def tearDown(self):
        for c in self.clientes:
            c.close()
        self.servidor.cerrar()
        self.app.processEvents()
        self.servidor.deleteLater()

    def recibir(self, i, texto):
        dato = json.loads(texto)
        self.mensajes[i].append(dato)
        if dato['tipo'] == 'estado':
            self.estados[i] = dato

    def enviar(self, i, **dato):
        dato = {'version': 1, **dato}
        if self.estados[i]:
            dato.setdefault('revision', self.estados[i]['revision'])
        self.clientes[i].sendTextMessage(json.dumps(dato))

    def iniciar(self):
        self.enviar(0, tipo='iniciar')
        self.esperar(lambda: all(e['partida'] for e in self.estados))

    def actuar(self, i, accion, total=None):
        previo = self.estados[i]['revision']
        self.enviar(i, tipo='accion', accion=accion, total=total, id_mano=self.estados[i]['partida']['id_mano'])
        self.esperar(lambda: all(e['revision'] > previo for e in self.estados))

    def test_privacidad_y_mano_completa_sin_motor_en_clientes(self):
        self.iniciar()
        for i in range(2):
            p = self.estados[i]['partida']
            self.assertTrue(all(p['jugadores'][i]['cartas']))
            self.assertEqual(p['jugadores'][1-i]['cartas'], [None, None])
            self.assertNotIn('baraja', p)
            self.assertNotIn('rng', p)
        pasos = 0
        while not self.estados[0]['partida']['terminada']:
            p = self.estados[0]['partida']
            if p['turno'] is None:
                rev = self.estados[0]['revision']
                self.esperar(lambda: self.estados[0]['revision'] > rev)
            else:
                self.actuar(p['turno'], 'call')
            pasos += 1
            self.assertLess(pasos, 30)
        for e in self.estados:
            self.assertEqual(len(e['partida']['mesa']), 5)
            self.assertEqual(sum(j['fichas'] for j in e['partida']['jugadores']), 4000)
            self.assertTrue(all(all(j['cartas']) for j in e['partida']['jugadores']))
        self.assertEqual(self.estados[0]['partida']['pagos'], self.estados[1]['partida']['pagos'])

    def test_fuera_de_turno_y_duplicados_no_cobran(self):
        self.iniciar()
        self.enviar(1, tipo='accion', accion='call', id_mano=self.estados[1]['partida']['id_mano'], asiento=0)
        self.esperar(lambda: any(d['tipo'] == 'error' for d in self.mensajes[1]))
        self.assertEqual(self.estados[0]['partida']['bote'], 60)
        rev = self.estados[0]['revision']
        mano = self.estados[0]['partida']['id_mano']
        self.actuar(0, 'call')
        self.enviar(0, tipo='accion', accion='call', id_mano=mano, revision=rev)
        self.esperar(lambda: any(d['tipo'] == 'error' for d in self.mensajes[0]))
        self.assertEqual(self.estados[0]['partida']['bote'], 80)

    def test_all_in_y_desconexion_cierran_sin_cartas_futuras(self):
        self.iniciar()
        self.actuar(0, 'raise', 2000)
        self.actuar(1, 'call')
        self.esperar(lambda: self.estados[0]['partida']['terminada'])
        self.assertEqual(sum(j['fichas'] for j in self.estados[0]['partida']['jugadores']), 4000)
        self.clientes[1].close()
        self.esperar(lambda: any(d['tipo'] == 'cerrada' for d in self.mensajes[0]))
        self.assertEqual(self.servidor.salas, {})

    def test_fold_no_revela_cartas_del_rival(self):
        self.iniciar()
        self.actuar(0, 'fold')
        for i in range(2):
            p = self.estados[i]['partida']
            self.assertTrue(p['terminada'])
            self.assertEqual(p['jugadores'][1-i]['cartas'], [None, None])

    def test_panel_dibuja_estado_y_envia_acciones(self):
        panel = PanelOnline(puerto=self.servidor.puerto)
        panel.nombre.setText('Tres')
        panel.codigo.setText(self.estados[0]['codigo'])
        panel.conectar('unir')
        try:
            self.esperar(lambda: panel.estado is not None)
            self.esperar(lambda: len(self.estados[0]['nombres']) == 3)
            self.iniciar()
            self.esperar(lambda: panel.estado['partida'] is not None)
            self.actuar(0, 'call')
            self.actuar(1, 'call')
            self.esperar(lambda: panel.vista.call.isEnabled())
            self.assertFalse(hasattr(panel, 'motor'))
            panel.vista.call.click()
            self.esperar(lambda: self.estados[0]['partida']['fase'] == 'Flop')
        finally:
            panel.cerrar()
            panel.deleteLater()

    def test_seis_jugadores_completan_una_mano(self):
        for i in range(2, 6):
            self.estados.append(None)
            self.mensajes.append([])
            socket = QWebSocket()
            socket.textMessageReceived.connect(lambda t, i=i: self.recibir(i, t))
            self.clientes.append(socket)
            socket.open(QUrl(f'ws://127.0.0.1:{self.servidor.puerto}'))
            self.esperar(socket.isValid)
            self.enviar(i, tipo='unir', nombre=f'Jugador {i}', codigo=self.estados[0]['codigo'])
            self.esperar(lambda: self.estados[i] is not None and len(self.estados[0]['nombres']) == i+1)
        self.iniciar()
        pasos = 0
        while not self.estados[0]['partida']['terminada']:
            p = self.estados[0]['partida']
            if p['turno'] is None:
                rev = self.estados[0]['revision']
                self.esperar(lambda: self.estados[0]['revision'] > rev)
            else:
                self.actuar(p['turno'], 'call')
            pasos += 1
            self.assertLess(pasos, 40)
        self.assertEqual(sum(j['fichas'] for j in self.estados[0]['partida']['jugadores']), 12000)
        self.assertTrue(all(e['partida']['pagos'] == self.estados[0]['partida']['pagos'] for e in self.estados))

    def test_json_invalido_no_rompe_la_sala(self):
        self.clientes[0].sendTextMessage('{')
        self.esperar(lambda: any(d['tipo'] == 'error' for d in self.mensajes[0]))
        self.iniciar()
        self.assertEqual(self.estados[0]['partida']['bote'], 60)
