from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QPushButton

import estilos


class Tecla(QPushButton):
    """Botón plano dibujado a mano. Puede mostrar texto o un dibujo (ícono)."""

    def __init__(self, texto: str = "", color: str = "#9AA3AD", dibujo=None, parent=None):
        super().__init__(texto, parent)
        self.color = QColor(color)
        self.dibujo = dibujo                   # función que dibuja el ícono, o None
        self._encima = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)        # no le saca el foco al texto que escribís
        fuente = QFont(estilos.FUENTE)
        fuente.setPixelSize(estilos.px(12))
        fuente.setWeight(QFont.DemiBold)
        self.setFont(fuente)

    def cambiar_dibujo(self, dibujo):
        self.dibujo = dibujo
        self.update()

    # --- Tamaño: según el texto, o cuadrada si es un dibujo ---------------------------
    def sizeHint(self) -> QSize:
        alto = estilos.px(24)
        if self.dibujo:
            return QSize(alto, alto)
        ancho = QFontMetrics(self.font()).horizontalAdvance(self.text()) + estilos.px(16)
        return QSize(max(alto, ancho), alto)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # --- Mouse encima: se aclara un poco ---------------------------------------------
    def enterEvent(self, evento):
        self._encima = True
        self.update()
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self._encima = False
        self.update()
        super().leaveEvent(evento)

    # --- Dibujo --------------------------------------------------------------------
    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        radio = estilos.px(6)

        base = QColor(self.color) if self.isEnabled() else QColor("#C5CED6")
        if self.isDown() or self.isChecked():
            base = base.darker(118)
        elif self._encima:
            base = base.lighter(108)

        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(base.darker(140), 1))
        p.setBrush(base)
        p.drawRoundedRect(r, radio, radio)

        if self.dibujo:
            lado = estilos.px(16)
            p.save()
            p.translate(r.center().x() - lado / 2, r.center().y() - lado / 2)
            self.dibujo(p, lado)               # dibuja el ícono en un cuadrado de 0 a "lado"
            p.restore()
        else:
            p.setPen(QColor(estilos.tinta_para(base)))
            p.setFont(self.font())
            p.drawText(r, Qt.AlignCenter, self.text())