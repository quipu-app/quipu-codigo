import json
import time
from math import pi, sin

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QWidget

import config
from comportamiento import Comportamiento, Estado
from globo import Globo

# Tiempos y alturas del salto
AGACHE = 0.18      # segundos agachado antes de saltar
VUELO = 0.50       # segundos en el aire
ATERRIZAJE = 0.20  # segundos agachado al caer (solo de cuerpo entero)
ALTURA_ARCO = 140  # píxeles que sube en el punto más alto del arco


def cargar_personaje(nombre: str):
    """Lee datos.json y recorta cada hoja en cuadros con nombre."""
    carpeta = config.CARPETA_PERSONAJES / nombre
    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))

    hojas = {}
    for modo, h in datos["hojas"].items():
        imagen = QPixmap(str(carpeta / h["sprite"]))
        if imagen.isNull():
            raise FileNotFoundError(f"No encontré {h['sprite']} en {carpeta}")
        g = h["grilla"]
        cols, w, alto = g["columnas"], g["cuadro_ancho"], g["cuadro_alto"]
        hojas[modo] = {
            gesto: imagen.copy((i % cols) * w, (i // cols) * alto, w, alto)
            for gesto, i in h["cuadros"].items()
        }
    return datos, hojas


class Personaje(QWidget):
    """La ventana flotante que muestra al personaje y le pasa datos al cerebro."""

    tocado = Signal()
    hablando = Signal(bool)   # True cuando empieza a hablar, False cuando termina

    def __init__(self, nombre: str, modo: str):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.datos, self.hojas = cargar_personaje(nombre)
        self.globo = Globo()
        self.modo = None
        self.cambiar_modo(modo)

        self._salto = None
        self._hablaba = False
        self.oclusor = None  # función que devuelve la zona que tapa a este personaje
        # datos del salto en curso, o None
        self._ultima_pos_cursor = QCursor.pos()
        self._press_pos = None
        self._offset_arrastre = None
        self._arrastrando = False

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.tic)
        self.reloj.start(config.INTERVALO_MS)

    # --- Modos -------------------------------------------------------------------
    def cambiar_modo(self, modo: str):
        pie_anterior = self.pie()
        self.modo = modo
        h = self.datos["hojas"][modo]
        self.hoja = h
        self.cuadros = self.hojas[modo]
        self.cuadro_w = h["grilla"]["cuadro_ancho"]
        self.cuadro_h = h["grilla"]["cuadro_alto"]
        self.escala = h["escala"]
        self.ancho = int(self.cuadro_w * self.escala)
        self.alto = int(self.cuadro_h * self.escala)
        self.resize(self.ancho, self.alto + config.MARGEN_SUP)

        self.cerebro = Comportamiento(
            self.datos["frases"], h["direcciones"],
            h["acciones_al_tocar"], h["acciones_solo"], time.monotonic(),
        )
        self.estado = Estado("mira_frente", 0.0, 1.0, None)
        if self.isVisible():
            self.ubicar_pie(pie_anterior)

    # --- El "pie": punto de apoyo (abajo al centro) ------------------------------
    def pie(self) -> QPoint:
        g = self.geometry()
        return QPoint(g.left() + g.width() // 2, g.bottom())

    def ubicar_pie(self, p: QPoint):
        self.move(p.x() - self.width() // 2, p.y() - self.height() + 1)

    @property
    def saltando(self) -> bool:
        return self._salto is not None

    # --- Acciones que pide el director ------------------------------------------
    def reaccionar(self):
        if not self.saltando:
            self.cerebro.tocar(time.monotonic())

    def decir(self, accion: str, frase: str):
        """Hace una acción con una frase. 'frase' puede ser una clave de datos.json o un texto."""
        if self.saltando:
            return
        frase = self.datos["frases"].get(frase) or config.FRASES_COMUNES.get(frase, frase)
        if "{nombre}" in frase:              # algunas frases usan el nombre de Ajustes
            from ajustes import ajustes
            frase = frase.replace("{nombre}", ajustes().get("nombre") or "")
        for opcion in (accion, "festeja", "saluda", "sonrie"):
            if opcion in self.cuadros:
                self.cerebro.hacer(opcion, time.monotonic(), frase)
                return

    def saltar(self, destino: QPoint, modo_final: str, al_terminar=None):
        """Salto en arco desde donde está hasta 'destino', terminando en 'modo_final'."""
        self.globo.hide()
        if self.modo != "cuerpo":
            self.cambiar_modo("cuerpo")    # para saltar necesita las piernas
        self._salto = {
            "t0": time.monotonic(),
            "origen": self.pie(),
            "destino": destino,
            "modo_final": modo_final,
            "al_terminar": al_terminar,
            "aterrizo": False,
        }

    def animar_salto(self, ahora: float):
        s = self._salto
        t = ahora - s["t0"]

        if t < AGACHE:
            gesto = "agachado"
        elif t < AGACHE + VUELO:
            gesto = "salto"
            p = (t - AGACHE) / VUELO
            o, d = s["origen"], s["destino"]
            x = o.x() + (d.x() - o.x()) * p
            y = o.y() + (d.y() - o.y()) * p - ALTURA_ARCO * sin(pi * p)
            self.ubicar_pie(QPoint(int(x), int(y)))
        else:
            if not s["aterrizo"]:
                s["aterrizo"] = True
                if s["modo_final"] != self.modo:
                    self.cambiar_modo(s["modo_final"])
                self.ubicar_pie(s["destino"])
                if s["al_terminar"]:
                    s["al_terminar"]()
            if self.modo == "cuerpo" and t < AGACHE + VUELO + ATERRIZAJE:
                gesto = "agachado"         # amortigua la caída
            else:
                self._salto = None
                return
        self.estado = Estado(gesto, 0.0, 1.0, None)

    # --- Geometría ---------------------------------------------------------------
    def rect_cabeza(self) -> QRect:
        return self.geometry().adjusted(0, config.MARGEN_SUP, 0, 0)

    def pos_cara(self) -> QPoint:
        cara = self.hoja["cara"]
        return self.mapToGlobal(QPoint(
            int(cara["x"] * self.escala),
            config.MARGEN_SUP + int(cara["y"] * self.escala),
        ))

    # --- Cada vuelta del reloj --------------------------------------------------
    def tic(self):
        ahora = time.monotonic()
        cursor = QCursor.pos()
        se_movio = cursor != self._ultima_pos_cursor
        self._ultima_pos_cursor = cursor

        if self.saltando:
            self.animar_salto(ahora)
            self.update()
            return

        cara = self.pos_cara()
        self.estado = self.cerebro.actualizar(
            ahora, cursor.x() - cara.x(), cursor.y() - cara.y(), se_movio
        )

        if self.estado.frase:
            if not self.globo.isVisible() or self.globo.texto != self.estado.frase:
                self.globo.mostrar(self.estado.frase, self.rect_cabeza())
            else:
                self.globo.ubicar(self.rect_cabeza())
        elif self.globo.isVisible():
            self.globo.hide()

        habla = bool(self.estado.frase)
        if habla != self._hablaba:
            self._hablaba = habla
            self.hablando.emit(habla)

        self.update()

    # --- Dibujo --------------------------------------------------------------
    def paintEvent(self, event):
        e = self.estado
        cuadro = self.cuadros.get(e.gesto, self.cuadros["mira_frente"])
        alto = self.alto * e.respiro
        ancho = self.ancho * (2 - e.respiro)
        destino = QRectF(
            (self.ancho - ancho) / 2,
            config.MARGEN_SUP + (self.alto - alto) - e.salto,
            ancho,
            alto,
        )
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.oclusor:
            zona = self.oclusor()
            if zona is not None:
                local = QRect(zona.topLeft() - self.geometry().topLeft(), zona.size())
                pintor.setClipRegion(QRegion(self.rect()).subtracted(QRegion(local)))
        pintor.drawPixmap(destino, cuadro, QRectF(0, 0, self.cuadro_w, self.cuadro_h))

    # --- Mouse -------------------------------------------------------------------
    def mousePressEvent(self, event):
        if self.saltando:
            return
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._offset_arrastre = self._press_pos - self.frameGeometry().topLeft()
            self._arrastrando = False
        elif event.button() == Qt.RightButton:
            menu = getattr(self, "al_click_derecho", None)   # el menú de Quipu (lo pone la bandeja)
            if menu:
                menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._press_pos is None or not (event.buttons() & Qt.LeftButton):
            return
        if self.modo == "medio":
            return                        # detrás de Quipu se mueve con la consola
        pos = event.globalPosition().toPoint()
        if not self._arrastrando and (pos - self._press_pos).manhattanLength() > 5:
            self._arrastrando = True
        if self._arrastrando:
            self.move(pos - self._offset_arrastre)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            if not self._arrastrando:
                self.tocado.emit()       # el director decide qué hacer
        self._press_pos = None
        self._arrastrando = False