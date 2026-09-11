ESTILO_BOTE = """
    color: #cfb477; 
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a2a, stop:1 #141414); 
    border: 1px solid #cfb477;
    border-radius: 12px;
"""

ESTILO_BOTONES_FIJOS = """
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #444444, stop:1 #222222);
        color: #E0E0E0;
        font-family: 'Segoe UI';
        font-weight: bold;
        font-size: 11px;
        border: 1px solid #111111;
        border-radius: 4px;
        padding: 6px 14px;
    }
    QPushButton:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #555555, stop:1 #333333);
        color: white;
    }
"""

ESTILO_SLIDER = """
    QSlider::groove:horizontal { 
        border: 1px solid #111111; height: 8px; 
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #333333, stop:1 #555555); border-radius: 4px; 
    }
    QSlider::sub-page:horizontal { 
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b0000, stop:1 #c61d23); border-radius: 4px; 
    }
    QSlider::handle:horizontal { 
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eeeeee, stop:1 #aaaaaa); 
        border: 1px solid #333333; width: 18px; margin-top: -5px; margin-bottom: -5px; border-radius: 9px; 
    }
"""

ESTILO_BOTONES_ACCION = """
    QPushButton { 
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #943b40, stop:1 #66292f); 
        color: white; font-family: 'Segoe UI'; font-weight: bold; font-size: 14px; 
        border: 1px solid #5a0508; border-radius: 6px; padding: 10px 30px; min-width: 100px; 
    }
    QPushButton:hover { 
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a34b50, stop:1 #793039); 
    }
"""
ESTILO_PESTANAS = """
    QTabWidget::pane {
        border: none;
        background-color: #121212;
    }
    QTabBar::tab {
        background-color: #222222;
        color: #A0A0A0;
        font-family: 'Segoe UI';
        font-weight: bold;
        font-size: 12px;
        padding: 8px 20px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        background-color: #2a2a2a;
        color: white;
    }
    QTabBar::tab:selected {
        background-color: #1a1a1a;
        color: #cfb477;
        border-bottom: 2px solid #cfb477;
    }
"""

ESTILO_TARJETA_STAT = """
    QWidget {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
    }
    QLabel {
        color: #ffffff;
        background: transparent;
        border: none;
    }
"""


ESTILO_PROGRESS_BAR = """
    QProgressBar {
        border: none;
        background-color: #2a2a2a;
        height: 6px;
        border-radius: 3px;
        text-align: transparent;
    }
    QProgressBar::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff007f, stop:1 #cfb477);
        border-radius: 3px;
    }
"""