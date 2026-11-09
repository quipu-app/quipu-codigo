from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen

import config


class Globo(QWidget):
    """Globito de diálogo que flota arriba de la cabeza del personaje."""

    PAD_X, PAD_Y, COLA = 16, 9, 10

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.texto = ""
        self.fuente = QFont("Segoe UI", 11, QFont.DemiBold)
        self.cola_izquierda = True  # True: el globo está a la derecha y la cola apunta a la izquierda

    SOLAPE = 20  # cuánto se mete el globo sobre la ventana del personaje

    def mostrar(self, texto: str, ref: QRect):
        self.texto = texto
        fm = QFontMetrics(self.fuente)
        self.resize(
            fm.horizontalAdvance(texto) + 2 * self.PAD_X + self.COLA,
            fm.height() + 2 * self.PAD_Y,
        )
        self.ubicar(ref)
        self.show()
        self.update()

    def ubicar(self, ref: QRect):
        pantalla = (QGuiApplication.screenAt(ref.center())
                    or QGuiApplication.primaryScreen()).availableGeometry()

        # A la altura de la cara, sin salirse de la pantalla por arriba ni por abajo
        y = ref.top() + int(ref.height() * 0.12)
        y = max(pantalla.top() + 4, min(y, pantalla.bottom() - self.height() - 4))

        # Primero a la derecha; si no entra, a la izquierda
        x = ref.right() - self.SOLAPE
        if x + self.width() <= pantalla.right() - 4:
            self.cola_izquierda = True
        else:
            x = ref.left() - self.width() + self.SOLAPE
            self.cola_izquierda = False

        self.move(x, y)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if self.cola_izquierda:
            cuerpo = QRectF(self.COLA + 1.5, 1.5, self.width() - self.COLA - 3, self.height() - 3)
            base_x, punta_x = cuerpo.left() + 1, 2
        else:
            cuerpo = QRectF(1.5, 1.5, self.width() - self.COLA - 3, self.height() - 3)
            base_x, punta_x = cuerpo.right() - 1, self.width() - 2

        forma = QPainterPath()
        forma.addRoundedRect(cuerpo, 14, 14)
        cola = QPainterPath()
        cy = cuerpo.top() + cuerpo.height() * 0.6
        cola.moveTo(base_x, cy - 8)
        cola.lineTo(punta_x, cy + 4)
        cola.lineTo(base_x, cy + 8)
        cola.closeSubpath()
        forma = forma.united(cola)

        p.setPen(QPen(QColor(config.GLOBO_TINTA), 2.5))
        p.setBrush(QColor(config.GLOBO_FONDO))
        p.drawPath(forma)
        p.setPen(QColor(config.GLOBO_TINTA))
        p.setFont(self.fuente)
        p.drawText(cuerpo, Qt.AlignCenter, self.texto)