from PySide6.QtGui import QColor, QFontDatabase
from paleta import COLOR_ORIGINAL, color_consola

import config

FUENTE = "Segoe UI"        # se reemplaza por Fredoka si está disponible
FUENTE_RETRO = "Consolas"  # para "Guardando...", estilo pantalla de calculadora
ESCALA_UI = 1.0            # la consola lo ajusta según el tamaño de Quipu

# Color de cada tecla de la carcasa, para que la pantalla de cada función combine
COLORES_TECLA = {
    "foco": "#F08A3C",      # naranja del reloj
    "notas": "#F2C94C",     # amarillo de la libreta
    "agenda": "#C8574A",    # rojo del calendario
    "clima": "#6BB8E0",     # celeste de la nube
    "sonidos": "#7FB86B",   # verde del parlante
    "ajustes": "#9AA3AD",   # gris del engranaje
}


def cargar_fuentes():
    """Registra Fredoka en la app. Hay que llamarla después de crear QApplication."""
    global FUENTE
    ruta = config.CARPETA_FUENTES / "Fredoka.ttf"
    if ruta.exists():
        familias = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(ruta)))
        if familias:
            FUENTE = familias[0]


def px(valor: float) -> int:
    """Convierte un tamaño pensado para Quipu chico al tamaño actual."""
    return max(1, round(valor * ESCALA_UI))


def tinta_para(fondo: QColor) -> str:
    """Texto oscuro sobre colores claros, blanco sobre colores oscuros."""
    luz = 0.299 * fondo.red() + 0.587 * fondo.green() + 0.114 * fondo.blue()
    return "#2B2B33" if luz > 150 else "#FFFFFF"


def qss_pantalla(modulo: str = "") -> str:
    """Hoja de estilos de la pantalla grande, con las teclas del color del módulo."""
    base = QColor(color_consola() or COLOR_ORIGINAL)  # el color del personaje, como en las pantallas web
    brillo = base.lighter(125).name()      # franja clara de arriba
    sombra = base.darker(155).name()       # relieve de abajo
    hundida = base.darker(115).name()      # tecla apretada o marcada
    tinta = tinta_para(base)
    return f"""
    #vista {{ background: #CFEFF8; border-radius: {px(10)}px; }}
    QWidget {{ font-family: "{FUENTE}"; color: #17324D; font-size: {px(11)}px; }}
    QLabel#titulo {{ font-size: {px(14)}px; font-weight: 700; }}
    QLabel#tiempo {{ font-size: {px(40)}px; font-weight: 700; }}
    QLabel#ayuda {{ font-size: {px(10)}px; color: #3A5A78; }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {brillo}, stop:0.22 {brillo}, stop:0.23 {base.name()}, stop:1 {base.name()});
        color: {tinta};
        border: {px(1.5)}px solid #2B2B33;
        border-bottom: {px(4)}px solid {sombra};
        border-radius: {px(7)}px;
        padding: {px(2)}px {px(6)}px;
        font-size: {px(11)}px; font-weight: 600;
        min-height: {px(16)}px;
    }}
    QPushButton:hover {{ background: {base.lighter(110).name()}; }}
    QPushButton:pressed, QPushButton:checked {{
        background: {hundida}; border-bottom-width: {px(1.5)}px; margin-top: {px(2)}px;
    }}
    QPushButton:disabled {{ background: #B8C4CE; color: #6E7B88; border-bottom-color: #8E9AA6; }}
    QLineEdit, QTextEdit, QListWidget, QComboBox {{
        background: #F4FBFD; border: 1px solid #8FB9C8; border-radius: {px(6)}px;
        font-size: {px(11)}px; padding: {px(1)}px {px(4)}px;
    }}
    QListWidget::item {{ padding: {px(2)}px; }}
    QListWidget::item:selected {{ background: #B7E3F0; color: #17324D; }}
    QProgressBar {{ background: #A9D6E3; border: none; border-radius: {px(3)}px; }}
    QProgressBar::chunk {{ background: {base.name()}; border-radius: {px(3)}px; }}
    QScrollBar:vertical {{ width: {px(6)}px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: #8FB9C8; border-radius: {px(3)}px; min-height: 20px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """