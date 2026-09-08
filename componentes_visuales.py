import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QFont, QPixmap  
from PySide6.QtCore import Qt

def obtener_ruta_imagen_carta(carta):
    """Mapea el objeto Carta con los nombres exactos de tu carpeta assets/cartas/"""
    dict_valores = {'2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10', 'J': 'jack', 'Q': 'queen', 'K': 'king', 'A': 'ace'}
    dict_palos = {'♠': 'spades', '♥': 'hearts', '♦': 'diamonds', '♣': 'clubs'}
    
    valor_ingles = dict_valores[carta.valor]
    palo_ingles = dict_palos[carta.palo]
    nombre_archivo = f"{valor_ingles}_of_{palo_ingles}.png"
    ruta_completa = os.path.join("assets", "cartas", nombre_archivo)
    
    if os.path.exists(ruta_completa):
        return ruta_completa
    return os.path.join("assets", "cartas", "ace_of_spades.png")

def crear_cuadro_perfil(parent, nombre, fichas, x, y):
    """Genera un widget estético oscuro para los asientos de la mesa con cartas ocultas incorporadas."""
    # 1. RENDERIZAR LAS DOS CARTAS BOCA ABAJO (Separación corregida a 48px)
    ruta_reverso = os.path.join("assets", "cartas", "back.png")
    if not os.path.exists(ruta_reverso):
        ruta_reverso = os.path.join("assets", "cartas", "ace_of_spades.png") 
        
    pixmap_back = QPixmap(ruta_reverso)
    
    if "Tú" not in nombre:
        for i in range(2):
            lbl_carta_oculta = QLabel(parent)
            if not pixmap_back.isNull():
                pix_escalado = pixmap_back.scaled(40, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                lbl_carta_oculta.setPixmap(pix_escalado)
            else:
                lbl_carta_oculta.setStyleSheet("background-color: #772222; border-radius: 3px;")
            
            lbl_carta_oculta.setFixedSize(40, 58)
            
            # MODIFICADO: Multiplicador a 48px y ajuste inicial para un centrado perfecto sobre el cuadro
            lbl_carta_oculta.move(x + 12 + (i * 40), y - 42)
            lbl_carta_oculta.show()

    # 2. CUADRO OSCURO DEL PERFIL
    estilo_perfil = "background-color: rgba(30, 30, 30, 230); color: white; border: 2px solid #555555; border-radius: 8px; padding: 5px;"
    panel = QWidget(parent)
    panel.setStyleSheet(estilo_perfil)
    panel.setFixedSize(140, 55)
    
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setSpacing(2)
    
    lbl_nombre = QLabel(nombre)
    lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_nombre.setFont(QFont("Arial", 9, QFont.Weight.Bold))
    lbl_nombre.setStyleSheet("color: #E0E0E0; border: none; background: transparent;")
    
    lbl_fichas = QLabel(fichas)
    lbl_fichas.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_fichas.setFont(QFont("Arial", 10))
    lbl_fichas.setStyleSheet("color: #A0A0A0; border: none; background: transparent;")
    
    layout.addWidget(lbl_nombre)
    layout.addWidget(lbl_fichas)
    panel.move(x, y)
    
    return {"nombre": lbl_nombre, "fichas": lbl_fichas}

def limpiar_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
