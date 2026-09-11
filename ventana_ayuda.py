from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from estadisticas import DEFINICIONES


class VentanaAyudaStats(QDialog):
    def __init__(self, clave, metrica, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cómo se calcula · {clave}")
        self.setMinimumWidth(450)
        self.setStyleSheet("QDialog { background: #1c1b21; } QLabel { color: #eeeeee; background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        titulo = QLabel(clave)
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ffcc;")
        layout.addWidget(titulo)
        explicacion = QLabel(DEFINICIONES[clave])
        explicacion.setWordWrap(True)
        layout.addWidget(explicacion)
        n, d = metrica["casos"], metrica["oportunidades"]
        calculo = f"Tu muestra: {n} / {d} × 100 = {metrica['porcentaje']:.1f} %" if d else "Sin oportunidades registradas todavía."
        layout.addWidget(QLabel(calculo))
        aviso = QLabel("El porcentaje describe esta muestra de práctica. Con pocas oportunidades puede cambiar mucho entre manos. Por sí solo no determina tu nivel ni si una decisión fue correcta.")
        aviso.setWordWrap(True)
        aviso.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(aviso)
        boton = QPushButton("Entendido")
        boton.clicked.connect(self.accept)
        layout.addWidget(boton)
