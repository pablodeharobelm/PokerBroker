import sys
import random
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                               QHBoxLayout, QVBoxLayout, QPushButton, QSlider,
                               QTabWidget, QProgressBar, QGridLayout, QScrollArea, QDialog)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtCore import Qt

# Importamos nuestros propios módulos separados
from logica_poker import Usuario, Baraja
import componentes_visuales as cv
import estilos as est  

class MesaDibujo(QWidget):
    """Clase especializada para pintar el tapete verde ovalado oficial dentro de su propia pestaña."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo oscuro exterior de la mesa
        painter.fillRect(self.rect(), QColor(25, 25, 25))
        
        # Dibujar el óvalo del tapete verde central ajustado a las dimensiones internas
        borde_grosor = 15
        pen = QPen(QColor(40, 40, 40), borde_grosor)
        painter.setPen(pen)
        
        brush = QBrush(QColor(10, 100, 45)) # Verde casino
        painter.setBrush(brush)
        
        # Coordenadas y dimensiones adaptadas para que cuadre perfecto en el layout
        painter.drawEllipse(50, 40, 900, 430)
class VentanaMesaPoker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IA Poker Trainer - Estilo PokerStars & Analíticas")
        self.setFixedSize(1020, 740)  
        
        self.jugador = Usuario("Finwa22", banco_inicial=10000)
        self.sesion = self.jugador.iniciar_sesion_mesa(2000)
        
        # Datos fijos de los asientos de los rivales
        self.datos_rivales = [
            {"nombre": "peco246", "fichas": "7,100", "x": 450, "y": 25},       
            {"nombre": "Breta232", "fichas": "9,921", "x": 800, "y": 120},     
            {"nombre": "Davidkim", "fichas": "10,884", "x": 800, "y": 300},    
            {"nombre": "_Yurec0816", "fichas": "2,850", "x": 40, "y": 300},    
            {"nombre": "FAKEL382", "fichas": "10,176", "x": 40, "y": 120},     
        ]
        
        self.baraja = None
        self.cartas_comunitarias_totales = []  
        self.mis_cartas_actuales = []  
        self.fase_actual = 0  
        self.bote_actual = 0
        self.apuesta_a_pagar = 0  
        self.cantidad_a_apostar = 0 
        self.asientos_visuales = {}
        
        # Inicializamos el tracker de oponentes
        from logica_poker import TrackerEstadisticasBots
        self.tracker_hud = TrackerEstadisticasBots()
        
        # --- ENRUTAMIENTO DE PESTAÑAS (QTabWidget) ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(est.ESTILO_PESTANAS)
        self.setCentralWidget(self.tabs)
        
        # Pestaña A: Usamos el componente especializado para recuperar el tapete verde ovalado
        self.tab_mesa = MesaDibujo()
        self.central_widget = self.tab_mesa  
        
        # Pestaña B: Contenedor para tu panel oscuro de estadísticas
        self.tab_stats = QWidget()
        
        self.tabs.addTab(self.tab_mesa, "🃏 MESA DE JUEGO")
        self.tabs.addTab(self.tab_stats, "📊 ESTADÍSTICAS PERFIL")
        
        # Ejecutamos las maquetaciones
        self.init_ui()
        self.init_stats_ui()  
        self.construir_asientos()
        self.iniciar_nueva_mano()
    def init_ui(self):
        """Distribuye la interfaz visual dividiendo el panel inferior en dos columnas laterales."""
        layout_principal = QVBoxLayout(self.tab_mesa)
        layout_principal.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_bote = QLabel("BOTE: 0", self.tab_mesa)
        self.lbl_bote.setFixedSize(180, 32)
        self.lbl_bote.move(410, 140)
        self.lbl_bote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bote.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_bote.setStyleSheet(est.ESTILO_BOTE)

        self.widget_centro = QWidget(self.tab_mesa)
        self.widget_centro.setFixedSize(450, 120)
        self.widget_centro.move(275, 195)
        self.layout_centro = QHBoxLayout(self.widget_centro)
        self.layout_centro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_centro.setSpacing(8)
        
        layout_principal.addStretch()
        
        # CONTENEDOR DE CONTROL INFERIOR SPLIT
        widget_split_inferior = QWidget()
        layout_split = QHBoxLayout(widget_split_inferior)
        layout_split.setContentsMargins(0, 0, 0, 0)
        layout_split.setSpacing(40) 
        
        # COLUMNA IZQUIERDA: Bloque Visual (Perfil, Cartas y HUD IA)
        widget_columna_izquierda = QWidget()
        layout_col_izq = QVBoxLayout(widget_columna_izquierda)
        layout_col_izq.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_col_izq.setSpacing(5)
        
        self.panel_mio = QWidget()
        self.panel_mio.setStyleSheet("background-color: rgba(30, 30, 30, 230); color: white; border: 2px solid #555555; border-radius: 8px; padding: 5px;")
        self.panel_mio.setFixedSize(140, 55)
        
        layout_texto_mio = QVBoxLayout(self.panel_mio)
        layout_texto_mio.setContentsMargins(5, 2, 5, 2)
        layout_texto_mio.setSpacing(2)
        
        self.lbl_nombre_propio = QLabel("Finwa22 (Tú)")
        self.lbl_nombre_propio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nombre_propio.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lbl_nombre_propio.setStyleSheet("color: #E0E0E0; border: none; background: transparent;")
        
        self.lbl_fichas_propias = QLabel("2,000")
        self.lbl_fichas_propias.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fichas_propias.setFont(QFont("Arial", 10))
        self.lbl_fichas_propias.setStyleSheet("color: #A0A0A0; border: none; background: transparent;")
        
        layout_texto_mio.addWidget(self.lbl_nombre_propio)
        layout_texto_mio.addWidget(self.lbl_fichas_propias)
        layout_col_izq.addWidget(self.panel_mio, alignment=Qt.AlignmentFlag.AlignCenter)
        
        widget_cartas_y_hud = QWidget()
        widget_cartas_y_hud = QWidget()
        layout_cartas_y_hud = QHBoxLayout(widget_cartas_y_hud)
        layout_cartas_y_hud.setContentsMargins(0, 0, 0, 0)
        layout_cartas_y_hud.setSpacing(15)
        
        self.panel_hud_ia = QWidget()
        self.panel_hud_ia.setFixedSize(250, 150)
        self.panel_hud_ia.setStyleSheet("background-color: rgba(12, 12, 12, 245); color: #26e600; border: 1px dashed #444444; border-radius: 6px; padding: 8px;")
        
        layout_textos_ia = QVBoxLayout(self.panel_hud_ia)
        layout_textos_ia.setContentsMargins(8, 8, 8, 8)
        layout_textos_ia.setSpacing(5)
        
        self.lbl_hud_posicion = QLabel("POSICIÓN: TBD")
        self.lbl_hud_posicion.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.lbl_hud_posicion.setStyleSheet("color: #26e600;")
        
        self.lbl_hud_equity = QLabel("JUGADA: Calculando...")
        self.lbl_hud_equity.setStyleSheet("color: #00bfff;")
        self.lbl_hud_equity.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        
        self.lbl_hud_consejo = QLabel("CONSEJO: Esperando...")
        self.lbl_hud_consejo.setStyleSheet("color: #EAEAEA;")
        self.lbl_hud_consejo.setFont(QFont("Segoe UI", 9))
        self.lbl_hud_consejo.setWordWrap(True)
        
        layout_textos_ia.addWidget(self.lbl_hud_posicion)
        layout_textos_ia.addWidget(self.lbl_hud_equity)
        layout_textos_ia.addWidget(self.lbl_hud_consejo)
        layout_textos_ia.addStretch()
        
        layout_cartas_y_hud.addWidget(self.panel_hud_ia)
        
        self.widget_cartas_fisicas = QWidget()
        self.layout_mano = QHBoxLayout(self.widget_cartas_fisicas)
        self.layout_mano.setContentsMargins(0, 0, 0, 0)
        self.layout_mano.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_cartas_y_hud.addWidget(self.widget_cartas_fisicas)
        
        layout_col_izq.addWidget(widget_cartas_y_hud, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_split.addWidget(widget_columna_izquierda)
        
        # COLUMNA DERECHA: Mandos (Slider y botones de Fold / Check / Raise)
        widget_columna_derecha = QWidget()
        layout_col_der = QVBoxLayout(widget_columna_derecha)
        layout_col_der.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_col_der.setSpacing(10)
        
        layout_slider_fila = QHBoxLayout()
        layout_slider_fila.setSpacing(8)
        
        self.btn_min = QPushButton("Min")
        self.btn_half = QPushButton("1/2 Pot")
        self.btn_pot = QPushButton("Pot")
        self.btn_max = QPushButton("Max")
        
        for btn in [self.btn_min, self.btn_half, self.btn_pot, self.btn_max]:
            btn.setStyleSheet(est.ESTILO_BOTONES_FIJOS)
            layout_slider_fila.addWidget(btn)

        self.btn_min.clicked.connect(lambda: self.fijar_tamano_apuesta("min"))
        self.btn_half.clicked.connect(lambda: self.fijar_tamano_apuesta("half"))
        self.btn_pot.clicked.connect(lambda: self.fijar_tamano_apuesta("pot"))
        self.btn_max.clicked.connect(lambda: self.fijar_tamano_apuesta("max"))
        layout_col_der.addLayout(layout_slider_fila)
        
        self.slider_apuestas = QSlider(Qt.Orientation.Horizontal)
        self.slider_apuestas.setFixedWidth(280)
        self.slider_apuestas.setSingleStep(10)
        self.slider_apuestas.setPageStep(50)
        self.slider_apuestas.setStyleSheet(est.ESTILO_SLIDER)
        self.slider_apuestas.valueChanged.connect(self.actualizar_valor_slider)
        layout_col_der.addWidget(self.slider_apuestas, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout_botones_fila = QHBoxLayout()
        layout_botones_fila.setSpacing(10)
        
        self.btn_fold = QPushButton("Fold")
        self.btn_call = QPushButton("Check")
        self.btn_raise = QPushButton("Bet / Raise")
        
        for btn in [self.btn_fold, self.btn_call, self.btn_raise]:
            btn.setStyleSheet(est.ESTILO_BOTONES_ACCION)
            layout_botones_fila.addWidget(btn)
            
        self.btn_call.clicked.connect(self.avanzar_fase_juego)
        self.btn_fold.clicked.connect(self.ejecutar_fold)
        self.btn_raise.clicked.connect(self.ejecutar_apuesta_raise)
        
        layout_col_der.addLayout(layout_botones_fila)
        layout_split.addWidget(widget_columna_derecha)
        layout_principal.addWidget(widget_split_inferior)

    def init_stats_ui(self):
        """Maqueta la pestaña de analíticas estructurando las métricas, el bloque de Fold y el Poker IQ Score."""
        layout_principal_stats = QVBoxLayout(self.tab_stats)
        layout_principal_stats.setContentsMargins(20, 20, 20, 20)
        
        lbl_seccion = QLabel("STATISTICS (HERO: Finwa22)")
        lbl_seccion.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_seccion.setStyleSheet("color: white;")
        layout_principal_stats.addWidget(lbl_seccion)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #121212; }")
        
        contenedor_scroll = QWidget()
        contenedor_scroll.setStyleSheet("background-color: #121212;")
        layout_grid = QGridLayout(contenedor_scroll)
        layout_grid.setSpacing(20)
        
        # --- FILA 1: ESTADÍSTICAS PRINCIPALES PRE-FLOP ---
        layout_grid.addWidget(self.crear_tarjeta_stat("⚡ VPIP", "36%", "Loose"), 0, 0)
        layout_grid.addWidget(self.crear_tarjeta_stat("⚔️ PFR", "28%", "Aggressive"), 0, 1)
        layout_grid.addWidget(self.crear_tarjeta_stat("🎯 ATS (Robo)", "36%", "Balanced"), 0, 2)
        layout_grid.addWidget(self.crear_tarjeta_stat("🔥 3-BET", "19%", "Maniac"), 0, 3)
        
        # --- FILA 2: ESTADÍSTICAS DE SHOWDOWN Y VOLUMEN ---
        layout_grid.addWidget(self.crear_tarjeta_stat("🏟️ WTSD", "62%", "Went to Showdown"), 1, 0)
        layout_grid.addWidget(self.crear_tarjeta_stat("🏆 WSD", "53%", "Won at Showdown"), 1, 1)
        layout_grid.addWidget(self.crear_tarjeta_stat("📈 WWSF", "37%", "Won When Saw Flop"), 1, 2)
        layout_grid.addWidget(self.crear_tarjeta_stat("✋ HANDS", "3597", "Total Played"), 1, 3)
        
        # --- FILA 3: BLOQUE CONTENEDOR UNIFICADO DE FRECUENCIAS DE FOLD ---
        widget_bloque_fold = QWidget()
        widget_bloque_fold.setStyleSheet("QWidget { background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; }")
        layout_bloque_fold = QVBoxLayout(widget_bloque_fold)
        layout_bloque_fold.setContentsMargins(15, 15, 15, 15)
        layout_bloque_fold.setSpacing(12)
        
        lbl_tit_calles = QLabel("📉 FOLD FREQUENCY BY STREET")
        lbl_tit_calles.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tit_calles.setStyleSheet("color: white; border: none; background: transparent;")
        layout_bloque_fold.addWidget(lbl_tit_calles)
        
        widget_tarjetas_internas = QWidget()
        widget_tarjetas_internas.setStyleSheet("border: none; background: transparent;")
        layout_tarjetas_h = QHBoxLayout(widget_tarjetas_internas)
        layout_tarjetas_h.setContentsMargins(0, 0, 0, 0)
        layout_tarjetas_h.setSpacing(15)
        
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 PF-FOLD", "63%", "Preflop Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 FLOP-FOLD", "17%", "Flop Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 TURN-FOLD", "16%", "Turn Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 RIVER-FOLD", "10%", "River Fold"))
        
        layout_bloque_fold.addWidget(widget_tarjetas_internas)
        layout_bloque_fold.addStretch()
        layout_grid.addWidget(widget_bloque_fold, 2, 0, 1, 4)

        # --- FILA 4: NUEVO BLOQUE CONTENEDOR DE POKER IQ ---
        widget_bloque_iq = QWidget()
        widget_bloque_iq.setStyleSheet("QWidget { background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; }")
        layout_bloque_iq = QVBoxLayout(widget_bloque_iq)
        layout_bloque_iq.setContentsMargins(15, 15, 15, 15)
        layout_bloque_iq.setSpacing(10)
        
        lbl_tit_iq = QLabel("🧠 POKER IQ SCORE - NOTA GLOBAL DE RENDIMIENTO")
        lbl_tit_iq.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tit_iq.setStyleSheet("color: white; border: none; background: transparent;")
        layout_bloque_iq.addWidget(lbl_tit_iq)
        
        widget_info_iq = QWidget()
        widget_info_iq.setStyleSheet("border: none; background: transparent;")
        layout_info_iq_h = QHBoxLayout(widget_info_iq)
        layout_info_iq_h.setContentsMargins(0, 0, 0, 0)
        
        lbl_numero_iq = QLabel("44%")
        lbl_numero_iq.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        lbl_numero_iq.setStyleSheet("color: #ff3366; border: none; background: transparent; padding-right: 15px;")
        layout_info_iq_h.addWidget(lbl_numero_iq)
        
        widget_detalles_iq = QWidget()
        layout_detalles_v = QVBoxLayout(widget_detalles_iq)
        layout_detalles_v.setContentsMargins(0, 0, 0, 0)
        layout_detalles_v.setSpacing(4)
        
        lbl_status_iq = QLabel("⚠️ DIAGNÓSTICO: Principiante / Fuga de Fichas Crítica (Calling Station)")
        lbl_status_iq.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_status_iq.setStyleSheet("color: #ff3366; border: none;")
        
        progreso_iq = QProgressBar()
        progreso_iq.setTextVisible(False)
        progreso_iq.setStyleSheet("""
            QProgressBar { border: none; background-color: #2a2a2a; height: 10px; border-radius: 5px; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0055, stop:1 #990022); border-radius: 5px; }
        """)
        progreso_iq.setValue(44)
        
        lbl_meta_iq = QLabel("Escala: 0-49% Crítico (Rojo) | 50-69% Regular (Amarillo) | 70-84% Avanzado (Verde) | 85%+ Master (Cian)")
        lbl_meta_iq.setFont(QFont("Segoe UI", 8))
        lbl_meta_iq.setStyleSheet("color: #666666; border: none;")
        
        layout_detalles_v.addWidget(lbl_status_iq)
        layout_detalles_v.addWidget(progreso_iq)
        layout_detalles_v.addWidget(lbl_meta_iq)
        
        layout_info_iq_h.addWidget(widget_detalles_iq, 1)
        layout_bloque_iq.addWidget(widget_info_iq)
        
        layout_grid.addWidget(widget_bloque_iq, 3, 0, 1, 4)
        
        layout_grid.setRowStretch(0, 1)
        layout_grid.setRowStretch(1, 1)
        layout_grid.setRowStretch(2, 1)
        layout_grid.setRowStretch(3, 1)
        
        scroll.setWidget(contenedor_scroll)
        layout_principal_stats.addWidget(scroll)
        
        lbl_consejo_global = QLabel("🎯 CONSEJO DEL ENTRENADOR IA: Tu VPIP/PFR indica un estilo Loose-Aggressive (LAG). Juegas muchas manos iniciales y vas demasiado al Showdown (WTSD: 62%). Tu frecuencia de fold post-flop (Flop: 17%, River: 10%) es alarmantemente baja, lo que demuestra que estás pagando apuestas con rangos marginales. ¡Aprende a foldear ante la agresión!")
        lbl_consejo_global.setFont(QFont("Segoe UI", 10))
        lbl_consejo_global.setStyleSheet("color: #00ffcc; padding-top: 10px;")
        lbl_consejo_global.setWordWrap(True)
        layout_principal_stats.addWidget(lbl_consejo_global)

        """Maqueta la pestaña de analíticas compactando el contenedor de Fold Frequency."""
        layout_principal_stats = QVBoxLayout(self.tab_stats)
        layout_principal_stats.setContentsMargins(20, 20, 20, 20)
        
        lbl_seccion = QLabel("STATISTICS (HERO: Finwa22)")
        lbl_seccion.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_seccion.setStyleSheet("color: white;")
        layout_principal_stats.addWidget(lbl_seccion)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #121212; }")
        
        contenedor_scroll = QWidget()
        contenedor_scroll.setStyleSheet("background-color: #121212;")
        layout_grid = QGridLayout(contenedor_scroll)
        layout_grid.setSpacing(20)
        
        # --- FILA 1: ESTADÍSTICAS PRINCIPALES PRE-FLOP ---
        layout_grid.addWidget(self.crear_tarjeta_stat("⚡ VPIP", "36%", "Loose"), 0, 0)
        layout_grid.addWidget(self.crear_tarjeta_stat("⚔️ PFR", "28%", "Aggressive"), 0, 1)
        layout_grid.addWidget(self.crear_tarjeta_stat("🎯 ATS (Robo)", "36%", "Balanced"), 0, 2)
        layout_grid.addWidget(self.crear_tarjeta_stat("🔥 3-BET", "19%", "Maniac"), 0, 3)
        
        # --- FILA 2: ESTADÍSTICAS DE SHOWDOWN Y VOLUMEN ---
        layout_grid.addWidget(self.crear_tarjeta_stat("🏟️ WTSD", "62%", "Went to Showdown"), 1, 0)
        layout_grid.addWidget(self.crear_tarjeta_stat("🏆 WSD", "53%", "Won at Showdown"), 1, 1)
        layout_grid.addWidget(self.crear_tarjeta_stat("📈 WWSF", "37%", "Won When Saw Flop"), 1, 2)
        layout_grid.addWidget(self.crear_tarjeta_stat("✋ HANDS", "3597", "Total Played"), 1, 3)
        
        # --- FILA 3: BLOQUE CONTENEDOR UNIFICADO DE FRECUENCIAS DE FOLD ---
        widget_bloque_fold = QWidget()
        widget_bloque_fold.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 12px;
            }
        """)
        
        layout_bloque_fold = QVBoxLayout(widget_bloque_fold)
        layout_bloque_fold.setContentsMargins(15, 15, 15, 15)
        layout_bloque_fold.setSpacing(12)
        
        lbl_tit_calles = QLabel("📉 FOLD FREQUENCY")
        lbl_tit_calles.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_tit_calles.setStyleSheet("color: white; border: none; background: transparent;")
        layout_bloque_fold.addWidget(lbl_tit_calles)
        
        widget_tarjetas_internas = QWidget()
        widget_tarjetas_internas.setStyleSheet("border: none; background: transparent;")
        layout_tarjetas_h = QHBoxLayout(widget_tarjetas_internas)
        layout_tarjetas_h.setContentsMargins(0, 0, 0, 0)
        layout_tarjetas_h.setSpacing(15)
        
        # Inyectamos las tarjetas interactivas compactas
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 PF-FOLD", "63%", "Preflop Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 FLOP-FOLD", "17%", "Flop Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 TURN-FOLD", "16%", "Turn Fold"))
        layout_tarjetas_h.addWidget(self.crear_tarjeta_stat("📉 RIVER-FOLD", "10%", "River Fold"))
        
        layout_bloque_fold.addWidget(widget_cartas_internas := widget_tarjetas_internas)
        
        # CORREGIDO: Añadimos un muelle vertical interno para que las tarjetas no se estiren hacia abajo
        layout_bloque_fold.addStretch()
        
        layout_grid.addWidget(widget_bloque_fold, 2, 0, 1, 4)
        
        # CORREGIDO: Forzamos a la fila del bloque de fold a ocupar solo el espacio necesario en el grid general
        layout_grid.setRowStretch(0, 1)
        layout_grid.setRowStretch(1, 1)
        layout_grid.setRowStretch(2, 1)
        
        scroll.setWidget(contenedor_scroll)
        layout_principal_stats.addWidget(scroll)
        
        lbl_consejo_global = QLabel("🎯 CONSEJO DEL ENTRENADOR IA: Tu VPIP/PFR indica un estilo Loose-Aggressive (LAG). Juegas muchas manos iniciales y vas demasiado al Showdown (WTSD: 62%). Tu frecuencia de fold post-flop (Flop: 17%, River: 10%) es alarmantemente baja, lo que demuestra que estás pagando apuestas con rangos marginales. ¡Aprende a foldear ante la agresión!")
        lbl_consejo_global.setFont(QFont("Segoe UI", 10))
        lbl_consejo_global.setStyleSheet("color: #00ffcc; padding-top: 10px;")
        lbl_consejo_global.setWordWrap(True)
        layout_principal_stats.addWidget(lbl_consejo_global)


    def construir_asientos(self):
        """Inicializa las referencias de las etiquetas de toda la mesa guardando bots e Héroe en paralelo."""
        # 1. Almacenamos los 5 rivales en nuestro diccionario (Asientos del 0 al 4) para evitar el KeyError
        for i, r in enumerate(self.datos_rivales):
            etiquetas = cv.crear_cuadro_perfil(self.tab_mesa, r["nombre"], r["fichas"], r["x"], r["y"])
            self.asientos_visuales[i] = etiquetas
            
        # 2. Anexamos tus propias etiquetas en claves independientes sin machacar la lista de los bots
        self.asientos_visuales["nombre"] = self.lbl_nombre_propio
        self.asientos_visuales["fichas"] = self.lbl_fichas_propias

    def iniciar_nueva_mano(self):
        self.fase_actual = 0
        self.bote_actual = 0
        self.lbl_bote.setText(f"BOTE: {self.bote_actual}")
        for btn in [self.btn_call, self.btn_raise, self.slider_apuestas, self.btn_min, self.btn_half, self.btn_pot, self.btn_max]:
            btn.setEnabled(True)
            
        self.apuesta_a_pagar = random.choice([0, 40, 100, 200])
        cv.limpiar_layout(self.layout_centro)
        cv.limpiar_layout(self.layout_mano)
        self.baraja = Baraja()
        cartas_propias = self.baraja.repartir(2)
        self.mis_cartas_actuales = cartas_propias  
        for carta in cartas_propias:
            lbl = QLabel()
            pix = QPixmap(cv.obtener_ruta_imagen_carta(carta))
            lbl.setPixmap(pix.scaled(75, 105, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.layout_mano.addWidget(lbl)
        self.cartas_comunitarias_totales = self.baraja.repartir(5)
        self.configurar_limites_slider()
        from logica_poker import GestorPosiciones
        gestor_pos = GestorPosiciones()
        indice_dealer_actual = random.randint(0, 5)
        posiciones_de_esta_mano = gestor_pos.obtener_posiciones_ronda(indice_dealer_actual)
        for i, r in enumerate(self.datos_rivales):
            pos_bot = posiciones_de_esta_mano[i]
            self.asientos_visuales[i]["nombre"].setText(f"[{pos_bot}] {r['nombre']}")
            texto_stats_actualizado = self.tracker_hud.simular_mano_y_calcular_hud(r["nombre"])
            
            if "hud" in self.asientos_visuales[i]:
                self.asientos_visuales[i]["hud"].setText(texto_stats_actualizado)
            elif "hud_stats" in self.asientos_visuales[i]:
                self.asientos_visuales[i]["hud_stats"].setText(texto_stats_actualizado)
                
        mi_pos_actual = posiciones_de_esta_mano  # El héroe es el asiento índice 5
        self.asientos_visuales["nombre"].setText(f"[{mi_pos_actual}] Finwa22 (Tú)")
        self.lbl_hud_posicion.setText(f"POSICIÓN: {mi_pos_actual}")
        if mi_pos_actual in ["BTN", "CO"]:
            self.lbl_hud_consejo.setText("CONSEJO: Posición tardía. Tienes ventaja. Ataca el bote si viene limpio.")
        elif mi_pos_actual in ["SB", "BB"]:
            self.lbl_hud_consejo.setText("CONSEJO: Ciega. Hablarás de primero post-flop. Juega defensivo.")
        else:
            self.lbl_hud_consejo.setText("CONSEJO: Posición temprana. Hablas primero. Rango de manos muy fuerte.")
        self.actualizar_textos_botones_accion()
        self.actualizar_analisis_mano_ia()

    def ejecutar_fold(self):
        cv.limpiar_layout(self.layout_mano)
        for ctrl in [self.btn_raise, self.slider_apuestas, self.btn_min, self.btn_half, self.btn_pot, self.btn_max]:
            ctrl.setDisabled(True)
        self.fase_actual = 3  
        self.btn_call.setText("Siguiente Mano")
        self.lbl_hud_posicion.setText("POSICIÓN: --")
        self.lbl_hud_equity.setText("JUGADA: Retirado")
        self.lbl_hud_consejo.setText("CONSEJO: Has foldeado. Esperando a que comience la próxima mano.")

    def configurar_limites_slider(self):
        fichas_en_mesa = self.sesion.fichas_actuales
        apuesta_minima = max(self.apuesta_a_pagar, 40)
        apuesta_minima = min(apuesta_minima, fichas_en_mesa)
        self.slider_apuestas.setMinimum(apuesta_minima)
        self.slider_apuestas.setMaximum(fichas_en_mesa)
        self.slider_apuestas.setValue(apuesta_minima)
        self.cantidad_a_apostar = apuesta_minima

    def actualizar_valor_slider(self, valor):
        valor_redondeado = round(valor / 10) * 10
        if valor_redondeado > self.slider_apuestas.maximum(): valor_redondeado = self.slider_apuestas.maximum()
        if valor_redondeado < self.slider_apuestas.minimum(): valor_redondeado = self.slider_apuestas.minimum()
        self.cantidad_a_apostar = valor_redondeado
        if self.apuesta_a_pagar > 0: self.btn_raise.setText(f"Raise To {self.cantidad_a_apostar}")
        else: self.btn_raise.setText(f"Bet {self.cantidad_a_apostar}")

    def fijar_tamano_apuesta(self, tipo):
        fichas_en_mesa = self.sesion.fichas_actuales
        if tipo == "min": self.slider_apuestas.setValue(self.slider_apuestas.minimum())
        elif tipo == "half": self.slider_apuestas.setValue(min(max(int(self.bote_actual / 2), self.slider_apuestas.minimum()), fichas_en_mesa))
        elif tipo == "pot": self.slider_apuestas.setValue(min(max(self.bote_actual, self.slider_apuestas.minimum()), fichas_en_mesa))
        elif tipo == "max": self.slider_apuestas.setValue(fichas_en_mesa)

    def actualizar_textos_botones_accion(self):
        self.asientos_visuales["fichas"].setText(f"{self.sesion.fichas_actuales}")
        if self.apuesta_a_pagar > 0:
            self.btn_call.setText(f"Call {self.apuesta_a_pagar}")
            self.btn_raise.setText(f"Raise To {self.cantidad_a_apostar}")
        else:
            self.btn_call.setText("Check")
            self.btn_raise.setText(f"Bet {self.cantidad_a_apostar}")

    def ejecutar_apuesta_raise(self):
        monto = self.cantidad_a_apostar
        if monto > self.sesion.fichas_actuales: return
        self.sesion.fichas_actuales -= monto
        self.bote_actual += monto
        self.lbl_bote.setText(f"BOTE: {self.bote_actual}")
        self.apuesta_a_pagar = 0
        self.avanzar_fase_juego()

    def avanzar_fase_juego(self):
        if self.btn_call.text() == "Siguiente Mano":
            self.iniciar_nueva_mano()
            return
        if self.apuesta_a_pagar > 0:
            self.sesion.fichas_actuales -= self.apuesta_a_pagar
            self.bote_actual += self.apuesta_a_pagar
            self.lbl_bote.setText(f"BOTE: {self.bote_actual}")
            self.apuesta_a_pagar = 0
        if self.fase_actual == 0:
            self.fase_actual = 1
            self.mostrar_cartas_en_centro(self.cartas_comunitarias_totales[0:3])
        elif self.fase_actual == 1:
            self.fase_actual = 2
            self.mostrar_cartas_en_centro(self.cartas_comunitarias_totales[3:4])
        elif self.fase_actual == 2:
            self.fase_actual = 3
            self.mostrar_cartas_en_centro(self.cartas_comunitarias_totales[4:5])
            self.btn_call.setText("Finalizar Mano")
        elif self.fase_actual == 3:
            self.sesion.fichas_actuales += self.bote_actual
            self.iniciar_nueva_mano()
        self.configurar_limites_slider()
        self.actualizar_textos_botones_accion()
        self.actualizar_analisis_mano_ia()

    def mostrar_cartas_en_centro(self, lista_cartas):
        for carta in lista_cartas:
            lbl = QLabel()
            pix = QPixmap(cv.obtener_ruta_imagen_carta(carta))
            lbl.setPixmap(pix.scaled(65, 95, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.layout_centro.addWidget(lbl)

    def actualizar_analisis_mano_ia(self):
        from logica_poker import EvaluadorManos, CalculadorEquity
        evaluador = EvaluadorManos()
        calculador_eq = CalculadorEquity()
        cartas_visibles_mesa = []
        if self.fase_actual == 1: cartas_visibles_mesa = self.cartas_comunitarias_totales[0:3]
        elif self.fase_actual == 2: cartas_visibles_mesa = self.cartas_comunitarias_totales[0:4]
        elif self.fase_actual == 3: cartas_visibles_mesa = self.cartas_comunitarias_totales[0:5]
        jugada_texto = evaluador.evaluar_mano(self.mis_cartas_actuales, cartas_visibles_mesa)
        self.lbl_hud_equity.setText(f"JUGADA: {jugada_texto}")
        equity_real = calculador_eq.simular_equity_montecarlo(self.mis_cartas_actuales, cartas_visibles_mesa)
        pos_limpia = self.lbl_hud_posicion.text().split()[-1] if " " in self.lbl_hud_posicion.text() else "TBD"
        if self.fase_actual == 3: self.lbl_hud_posicion.setText(f"POSICIÓN: {pos_limpia} | EQ: Final")
        else: self.lbl_hud_posicion.setText(f"POSICIÓN: {pos_limpia} | EQ: {equity_real}%")

class VentanaAyudaStats(QDialog):
    """Ventana emergente premium que replica de forma exacta las barras de rangos con jerga real de póker."""
    def __init__(self, titulo_stat, dato_llave, valor_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Poker Academy - {titulo_stat}")
        self.setFixedSize(440, 500) 
        self.setStyleSheet("QDialog { background-color: #1c1b21; border: none; border-top-left-radius: 20px; border-top-right-radius: 20px; } QLabel { border: none; background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)
        
        # --- CONFIGURACIÓN DE DATOS CON EXPLICACIONES EN PERFECTO ESPAÑOL TÉCNICO ---
        config_stats = {
            "VPIP": {
                "icono": "✌️", "titulo": "Voluntarily Put In Pot",
                "nombres": ["Nit / Rock", "Tight", "TAG (Óptimo)", "LAG (Loose)", "Fish / Whale"],
                "rangos": ["0-10", "11-20", "21-30", "31-40", "40+"], "limites_raw": "10-20-30-40", "color": "#ff007f",
                "desc": "Mide el porcentaje de veces que entras voluntariamente al bote preflop (pagando o subiendo). Un VPIP óptimo en mesas 6-Max se sitúa entre el 21% y el 30% (estilo Tight-Aggressive). Valores superiores indican que juegas demasiadas manos débiles fuera de posición."
            },
            "PFR": {
                "icono": "🦬", "titulo": "Preflop Raise",
                "nombres": ["Pasivo / Nit", "Weak-Passive", "TAG (Óptimo)", "LAG (Agresivo)", "Maniac"],
                "rangos": ["0-5", "6-12", "13-20", "21-30", "30+"], "limites_raw": "5-12-20-30", "color": "#ff007f",
                "desc": "Muestra el porcentaje de veces que entras al bote subiendo la apuesta preflop. La agresividad es clave para tomar la iniciativa y generar fold equity. Tu PFR debe estar muy cerca de tu VPIP; si la brecha es grande, tu juego es demasiado pasivo."
            },
            "ATS": {
                "icono": "🦅", "titulo": "Attempt To Steal",
                "nombres": ["Tight / Nit", "Conservador", "Equilibrado", "Agresivo", "Maniac"],
                "rangos": ["0-15", "16-25", "26-40", "41-55", "55+"], "limites_raw": "15-25-40-55", "color": "#ff007f",
                "desc": "Rastrea los intentos de robo de ciegas desde posiciones de corte (CO), botón (BTN) o ciega pequeña (SB) cuando la mesa viene limpia. Aprovechar la ventaja posicional para llevarse el dinero muerto preflop es una de las métricas más rentables."
            },
            "3-BET": {
                "icono": "☝️", "titulo": "Three Bet",
                "nombres": ["Nit / Lineal", "Tight", "TAG (Óptimo)", "LAG (Agresivo)", "Maniac"],
                "rangos": ["0-2", "3-4", "5-7", "8-12", "12+"], "limites_raw": "2-4-7-12", "color": "#ff007f",
                "desc": "Mide la frecuencia con la que haces una resubida preflop ante una apertura previa. Un rango de 3-bet óptimo (5% al 7% o superior) equilibra manos premium por valor y faroles con bloqueadores para presionar los rangos del rival."
            },
            "WTSD": {
                "icono": "🤘", "titulo": "Went To Showdown",
                "nombres": ["Nit / Weak", "Tight", "Óptimo", "Loose", "Calling Station"],
                "rangos": ["0-20", "21-24", "25-28", "29-32", "32+"], "limites_raw": "20-24-28-32", "color": "#00ffcc",
                "desc": "Muestra el porcentaje de veces que llegas al showdown final tras haber visto el Flop. Un valor verídico y rentable oscila entre el 25% y un 28%. Superar el 32% indica un grave error de 'Calling Station' (pagar de más persiguiendo proyectos rotos)."
            },
            "WSD": {
                "icono": "🫰", "titulo": "Won At Showdown",
                "nombres": ["Eficiencia Baja", "Por Debajo", "Óptimo", "Excelente", "Rango Ultra-Tight"],
                "rangos": ["0-40", "41-45", "46-57", "57+", "100"], "limites_raw": "40-45-57-100", "color": "#00ffcc",
                "desc": "Mide qué porcentaje de las veces que muestras tus cartas en el showdown terminas ganando el bote. Mantener un ratio por encima del 46% demuestra una gran selección de manos para el 'Value Betting' y una correcta lectura de rangos postflop."
            },
            "WWSF": {
                "icono": "👌", "titulo": "Won When Saw Flop",
                "nombres": ["Pasivo / Débil", "Por Debajo", "Óptimo", "Excelente", "Hiper-Agresivo"],
                "rangos": ["0-37", "38-42", "43-47", "47+", "100"], "limites_raw": "37-42-47-100", "color": "#ff3366",
                "desc": "Muestra con qué frecuencia ganas el bote tras haber visto el Flop, ya sea ligando la mejor jugada o forzando el fold del rival en Turn o River. Evalúa tu agresividad y destreza técnica general para pelear botes postflop."
            },
            "HANDS": {
                "icono": "✋", "titulo": "Hands Played",
                "nombres": ["Muestra Corta", "Muestra Baja", "Muestra Fiable", "Muestra Alta", "Muestra Verificada"],
                "rangos": ["0-100", "101-500", "501-1500", "1501-3000", "3000+"], "limites_raw": "100-500-1500-3000", "color": "#00bfff",
                "desc": "Indica el volumen total de manos registradas en tu base de datos local. El póker está sujeto a una gran varianza a corto plazo; las estadísticas del HUD solo empiezan a ser matemáticamente fiables a partir de las 500 o 1000 manos."
            },
            "PF-FOLD": {
                "icono": "📉", "titulo": "Preflop Fold Frequency",
                "nombres": ["Hiper-Agresivo", "Agresivo", "TAG (Óptimo)", "Tight", "Nit / Amarrado"],
                "rangos": ["0-50", "51-59", "60-68", "69-75", "75+"], "limites_raw": "50-59-68-75", "color": "#ff007f",
                "desc": "Mide con qué frecuencia foldeas tus cartas antes del flop. En mesas 6-Max, retirarse entre el 60% y el 68% de las manos iniciales desde una perspectiva global es el estándar verídico para mantener un estilo Tight-Aggressive ganador."
            },
            "FLOP-FOLD": {
                "icono": "📉", "titulo": "Flop Fold Frequency",
                "nombres": ["Calling Fish", "Flotador", "Óptimo", "Equilibrado", "Weak / Débil"],
                "rangos": ["0-25", "26-34", "35-45", "46-55", "55+"], "limites_raw": "25-34-45-55", "color": "#ff3366",
                "desc": "Mide cuántas veces foldeas en el Flop ante una apuesta tras haber visto las tres primeras cartas comunitarias. Un ratio inferior al 25% (como tu 17%) indica que estás flotando demasiado y pagando con proyectos débiles o parejas marginales."
            },
            "TURN-FOLD": {
                "icono": "📉", "titulo": "Turn Fold Frequency",
                "nombres": ["Calling Fish", "Flotador", "Óptimo", "Equilibrado", "Weak / Débil"],
                "rangos": ["0-28", "29-37", "38-44", "45-52", "52+"], "limites_raw": "28-37-44-52", "color": "#ff3366",
                "desc": "Mide con qué frecuencia abandonas tu mano en el Turn al enfrentarte a una segunda apuesta ('second barrel') del rival. Mantener este ratio equilibrado (38-44%) evita que desangres tus fichas antes de ver la última calle."
            },
            "RIVER-FOLD": {
                "icono": "📉", "titulo": "River Fold Frequency",
                "nombres": ["Calling Station", "Pagador", "Óptimo", "Equilibrado", "Weak / Débil"],
                "rangos": ["0-30", "31-39", "40-45", "46-52", "52+"], "limites_raw": "30-39-45-52", "color": "#ff3366",
                "desc": "Mide tu tendencia a foldear en la última calle (River) frente a una tercera apuesta del rival ('third barrel'). Un fold del 40-45% es vital para no pagar botes gigantes con manos batidas. Tu 10% actual es una fuga crítica de fichas."
            }
        }
        
        cfg = config_stats.get(dato_llave, config_stats["VPIP"])
        limites_convertidos = [int(x) for x in cfg["limites_raw"].split("-")]
        segmento_activo = 4 
        for idx, limite in enumerate(limites_convertidos):
            if valor_actual <= limite: segmento_activo = idx; break
                
        lbl_icono = QLabel(cfg["icono"]); lbl_icono.setFont(QFont("Segoe UI", 32)); lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(lbl_icono)
        lbl_titulo = QLabel(cfg["titulo"]); lbl_titulo.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold)); lbl_titulo.setStyleSheet("color: #FFFFFF;"); lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(lbl_titulo)
        layout.addSpacing(10)
        
        widget_rangos = QWidget(); layout_rangos_v = QVBoxLayout(widget_rangos); layout_rangos_v.setContentsMargins(0, 0, 0, 0); layout_rangos_v.setSpacing(6)
        layout_barras_h = QHBoxLayout(); layout_barras_h.setSpacing(6)
        layout_perfiles_h = QHBoxLayout(); layout_numeros_h = QHBoxLayout()
        for idx in range(5):
            lbl_barra = QLabel(); lbl_barra.setFixedHeight(5)
            lbl_perf = QLabel(cfg["nombres"][idx]); lbl_perf.setFont(QFont("Segoe UI", 8)); lbl_perf.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_num = QLabel(cfg["rangos"][idx]); lbl_num.setFont(QFont("Segoe UI", 8)); lbl_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if idx == segmento_activo:
                lbl_barra.setStyleSheet(f"background-color: {cfg['color']}; border-radius: 2px;")
                lbl_perf.setStyleSheet("color: #FFFFFF; font-weight: bold;")
                lbl_num.setStyleSheet(f"color: {cfg['color']}; font-weight: bold;")
            else:
                lbl_barra.setStyleSheet("background-color: #2b2a32; border-radius: 2px;")
                lbl_perf.setStyleSheet("color: #616066;"); lbl_num.setStyleSheet("color: #616066;")
            layout_barras_h.addWidget(lbl_barra); layout_perfiles_h.addWidget(lbl_perf); layout_numeros_h.addWidget(lbl_num)
            
        layout_rangos_v.addLayout(layout_barras_h); layout_rangos_v.addLayout(layout_perfiles_h); layout_rangos_v.addLayout(layout_numeros_h); layout.addWidget(widget_rangos)
        layout.addSpacing(10)
        
        lbl_info = QLabel(cfg["desc"]); lbl_info.setFont(QFont("Segoe UI", 10)); lbl_info.setStyleSheet("color: #9c9ba3; line-height: 16px;"); lbl_info.setWordWrap(True); lbl_info.setAlignment(Qt.AlignmentFlag.AlignJustify); layout.addWidget(lbl_info)
        layout.addStretch()
        
        btn_cerrar = QPushButton("↩️  Entendido"); btn_cerrar.setFixedHeight(46); btn_cerrar.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #000000; border-radius: 23px; font-family: 'Segoe UI'; font-size: 13px; font-weight: bold; } QPushButton:hover { background-color: #e6e6e6; }")
        btn_cerrar.clicked.connect(self.accept); layout.addWidget(btn_cerrar)

    @staticmethod
    def lanzar_ayuda(parent, titulo, clave, valor_num):
        diag = VentanaAyudaStats(titulo, clave, valor_num, parent)
        diag.exec()

# Enlazamos el parche dinámicamente a la clase principal
VentanaMesaPoker.crear_tarjeta_stat = lambda self, titulo, valor, subtitulo: self._ejecutar_creacion_tarjeta(titulo, valor, subtitulo)

def _parche_crear_tarjeta(self, titulo, valor, subtitulo):
    tarjeta = QWidget(); tarjeta.setStyleSheet(est.ESTILO_TARJETA_STAT); tarjeta.setFixedSize(210, 100)
    tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
    
    layout_grid = QGridLayout(tarjeta); layout_grid.setContentsMargins(12, 10, 12, 10); layout_grid.setSpacing(2)
    lbl_tit = QLabel(titulo); lbl_tit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); lbl_tit.setStyleSheet("color: #BBBBBB; border: none; background: transparent;"); layout_grid.addWidget(lbl_tit, 0, 0, 1, 2)
    
    lbl_val = QLabel(valor); lbl_val.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold)); lbl_val.setStyleSheet("color: #FFFFFF; border: none; background: transparent;"); layout_grid.addWidget(lbl_val, 1, 0, 1, 2)
    progreso = QProgressBar(); progreso.setTextVisible(False); progreso.setStyleSheet(est.ESTILO_PROGRESS_BAR)
    
    clave_limpia = "".join(c for c in titulo if c.isalnum() or c == "-").replace("3BET", "3-BET").replace("THREEBET", "3-BET")
    valor_num = int(valor.replace('%', '').replace(',', '')) if (valor.replace('%', '').replace(',', '')).isdigit() else 50
    
    progreso_mapeado = 50 
    if "VPIP" in clave_limpia or "PFR" in clave_limpia: progreso_mapeado = min(int((valor_num / 40) * 100), 100)
    elif "ATS" in clave_limpia: progreso_mapeado = min(int((valor_num / 60) * 100), 100)
    elif "3-BET" in clave_limpia: progreso_mapeado = min(int((valor_num / 20) * 100), 100)
    elif "WTSD" in clave_limpia or "WWSF" in clave_limpia: progreso_mapeado = min(int((valor_num / 60) * 100), 100)
    elif "FOLD" in clave_limpia:
        if "PF" in clave_limpia: progreso_mapeado = min(int((valor_num / 68) * 100), 100)
        else: progreso_mapeado = min(int((valor_num / 45) * 100), 100)
    else: progreso_mapeado = min(valor_num, 100)
    progreso.setValue(progreso_mapeado); layout_grid.addWidget(progreso, 2, 0, 1, 2)
    
    lbl_sub = QLabel(subtitulo); lbl_sub.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    texto_diagnostico = subtitulo; color_diagnostico = "#999999"
    if "VPIP" in clave_limpia:
        if valor_num > 30: texto_diagnostico, color_diagnostico = "⚠️ Rango Loose (Excesivo)", "#ff3366"
        elif 21 <= valor_num <= 30: texto_diagnostico, color_diagnostico = "🟢 Rango TAG (Óptimo)", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Rango Nit (Muy Pasivo)", "#ffd700"
    elif "PFR" in clave_limpia:
        if valor_num > 25: texto_diagnostico, color_diagnostico = "⚠️ Agresivo Excesivo", "#ff3366"
        elif 13 <= valor_num <= 20: texto_diagnostico, color_diagnostico = "🟢 Rango TAG (Óptimo)", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Pasivo / Weak", "#ffd700"
    elif "ATS" in clave_limpia:
        if 26 <= valor_num <= 40: texto_diagnostico, color_diagnostico = "🟢 Robo Preflop Óptimo", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Conservador / Nit", "#ffd700"
    elif "3-BET" in clave_limpia:
        if valor_num > 12: texto_diagnostico, color_diagnostico = "🔴 Rango Maníaco (Peligro)", "#ff3366"
        elif 5 <= valor_num <= 7: texto_diagnostico, color_diagnostico = "🟢 Frecuencia TAG Óptima", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Rango Lineal / Predecible", "#ffd700"
    elif "WTSD" in clave_limpia:
        if valor_num > 32: texto_diagnostico, color_diagnostico = "🔴 Calling Station (Error)", "#ff3366"
        elif 25 <= valor_num <= 28: texto_diagnostico, color_diagnostico = "🟢 Showdown Óptimo", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Weak / Foldeas de más", "#ffd700"
    elif "WSD" in clave_limpia:
        if valor_num >= 46: texto_diagnostico, color_diagnostico = "🟢 Value Betting Alto", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Eficiencia Baja", "#ffd700"
    elif "WWSF" in clave_limpia:
        if 43 <= valor_num <= 47: texto_diagnostico, color_diagnostico = "🟢 Juego Post-flop Óptimo", "#00ffcc"
        else: texto_diagnostico, color_diagnostico = "🟡 Poco Agresivo", "#ffd700"
    elif "FOLD" in clave_limpia:
        if "PF" in clave_limpia:
            if 60 <= valor_num <= 68: texto_diagnostico, color_diagnostico = "🟢 Fold Preflop Óptimo", "#00ffcc"
            else: texto_diagnostico, color_diagnostico = "🟡 Frecuencia Desviada", "#ffd700"
        elif "FLOP" in clave_limpia or "TURN" in clave_limpia or "RIVER" in clave_limpia:
            if valor_num < 25: texto_diagnostico, color_diagnostico = "🔴 Calling Station (Error)", "#ff3366"
            else: texto_diagnostico, color_diagnostico = "🟢 Defensa Equilibrada", "#00ffcc"
    elif "HANDS" in clave_limpia: texto_diagnostico, color_diagnostico = "📈 Historial Héroe", "#00bfff"
        
    lbl_sub.setText(texto_diagnostico); lbl_sub.setStyleSheet(f"color: {color_diagnostico} !important; border: none; background: transparent;"); layout_grid.addWidget(lbl_sub, 3, 0, 1, 2)
    
    def mousePressEvent(event):
        if event.button() == Qt.MouseButton.LeftButton:
            VentanaAyudaStats.lanzar_ayuda(tarjeta, titulo, clave_limpia, valor_num)
    tarjeta.mousePressEvent = mousePressEvent
    return tarjeta

VentanaMesaPoker._ejecutar_creacion_tarjeta = _parche_crear_tarjeta

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaMesaPoker()
    ventana.show()
    sys.exit(app.exec())
