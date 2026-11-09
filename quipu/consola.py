import importlib
import json
import math
import time

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QLabel, QStackedWidget, QVBoxLayout, QWidget
from paleta import carpeta_consola, color_consola, recolorear

import config
import estilos
from sonido import Efectos


# --- Ayudantes de animación --------------------------------------------------
def tramo(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a)))

def suave_salida(x):
    return 1 - (1 - x) ** 3

def suave_entrada(x):
    return x ** 3

def rebote_salida(x, k=1.6):
    x -= 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2

def silueta(pix: QPixmap) -> QPixmap:
    s = QPixmap(pix.size())
    s.fill(Qt.transparent)
    p = QPainter(s)
    p.drawPixmap(0, 0, pix)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(s.rect(), QColor(0, 0, 0))
    p.end()
    return s

def cargar_modulos() -> dict:
    """Crea una instancia de cada módulo anotado en config.MODULOS."""
    modulos = {}
    for id_boton, ruta in config.MODULOS.items():
        archivo, clase = ruta.rsplit(".", 1)
        modulos[id_boton] = getattr(importlib.import_module(archivo), clase)()
    return modulos

def vista_simple(titulo: str, texto: str) -> QWidget:
    """Pantalla de texto para el inicio y para los botones sin módulo todavía."""
    v = QWidget()
    v.setObjectName("vista")
    v.setAttribute(Qt.WA_StyledBackground)
    v.setStyleSheet(estilos.qss_pantalla())
    t = QLabel(titulo)
    t.setStyleSheet("font-size: 18px; font-weight: 700;")
    d = QLabel(texto)
    d.setStyleSheet("font-size: 12px;")
    d.setWordWrap(True)
    for w in (t, d):
        w.setAlignment(Qt.AlignCenter)
    caja = QVBoxLayout(v)
    caja.addStretch()
    caja.addWidget(t)
    caja.addWidget(d)
    caja.addStretch()
    return v


class Consola(QWidget):
    """La ventana de Quipu."""

    cerrada = Signal()
    cerrar_pedido = Signal()
    movida = Signal(QPoint)
    evento = Signal(str, str, str)       # reenvía los avisos de los módulos al director

    DURACION_ABRIR = 1.9
    DURACION_CERRAR = 0.8
    DURACION_ANUNCIO = 1.5               # segundos que la pantallita muestra el nombre del botón

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        carpeta, consola_propia = carpeta_consola()
        self.datos = json.loads((carpeta / "quipu.json").read_text(encoding="utf-8"))
        interior = QPixmap(str(carpeta / self.datos["interior"]))
        self.tapa = QPixmap(str(carpeta / self.datos["tapa"]))
        if interior.isNull() or self.tapa.isNull():
            raise FileNotFoundError(f"Faltan imágenes de Quipu en {carpeta}")
        color = color_consola()
        if color and not consola_propia:
            interior = recolorear(interior, "interior", color)
            self.tapa = recolorear(self.tapa, "tapa", color)

        self.bisagra = self.datos["bisagra_x"]
        self.izquierda = interior.copy(0, 0, self.bisagra, interior.height())
        self.derecha = interior.copy(self.bisagra, 0,
                                     interior.width() - self.bisagra, interior.height())
        self.izquierda_sombra = silueta(self.izquierda)
        self.tapa_sombra = silueta(self.tapa)

        # Tamaño según la pantalla: ancho según config, sin pasarse del 85% del alto
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.escala = pantalla.width() * config.TAMANO_CONSOLA / interior.width()
        self.escala = min(self.escala, pantalla.height() * 0.85 / interior.height())
        estilos.ESCALA_UI = interior.width() * self.escala / 650  # 650 = ancho de Quipu "chico"
        self.resize(int(interior.width() * self.escala),
                    int(interior.height() * self.escala))

        self.abierta = False
        self._fase = None
        self._t0 = 0.0
        self._sobre_cerrar = False
        self._ultimo_arrastre = None
        self._anuncio = ""
        self._anuncio_hasta = 0.0
        self._apretado = None            # (id del botón, hasta cuándo se ve hundido)
        self._hablando = False
        self._guardado_t0 = -10.0
        self._proceso = ("Guardando", "Listo")
        self._aviso = ""
        self._aviso_t0 = -100.0
        self.setMouseTracking(True)
        self.efectos = Efectos()
        self.solo = None    # si tiene un id, es la única tecla que se puede usar (bienvenida)

        # --- Pantalla grande: una "pila" de vistas, se muestra una a la vez ---
        self.pantalla = QStackedWidget(self)
        r = self.datos["pantalla"]
        borde = 16  # margen para no tapar el marco oscuro de la pantalla (en píxeles de la imagen)
        self.pantalla.setGeometry(
            int((r["x"] + borde) * self.escala), int((r["y"] + borde) * self.escala),
            int((r["w"] - 2 * borde) * self.escala), int((r["h"] - 2 * borde) * self.escala),
        )
        self.vistas = {"inicio": vista_simple("¿Qué hacemos?", "Elegí un botón de Quipu")}
        self.pantalla.addWidget(self.vistas["inicio"])
        self.pantalla.hide()

        self.modulos = cargar_modulos()
        for id_boton, modulo in self.modulos.items():
            modulo.evento.connect(self.evento)
            modulo.guardado.connect(self.mostrar_guardado)
            modulo.proceso.connect(self.mostrar_proceso)
            modulo.aviso.connect(self.mostrar_aviso)
            self.vistas[id_boton] = modulo.crear_vista()
            self.pantalla.addWidget(self.vistas[id_boton])

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.tic)

    # --- Abrir y cerrar ----------------------------------------------------------
    def abrir(self):
        pantalla = QApplication.primaryScreen().availableGeometry()
        margen = 12
        self.move(pantalla.right() - self.width() - margen,
                  pantalla.bottom() - self.height() - margen)
        self.abierta = True
        self._fase = "abrir"
        self._t0 = time.monotonic()
        self.pantalla.setCurrentWidget(self.vistas["inicio"])
        self.show()
        self.reloj.start(16)

    def cerrar(self):
        self.abierta = False
        self._fase = "cerrar"
        self._t0 = time.monotonic()
        self.pantalla.hide()

    def tic(self):
        t = time.monotonic() - self._t0
        if self._fase == "abrir" and t >= self.DURACION_ABRIR:
            self._fase = "abierta"
            self.pantalla.show()
            self.reloj.setInterval(50)
        elif self._fase == "cerrar" and t >= self.DURACION_CERRAR:
            self._fase = None
            self.reloj.stop()
            self.hide()
            self.cerrada.emit()
            return
        self.update()

    # --- Botones de la carcasa -----------------------------------------------------
    def boton_en(self, pos) -> str | None:
        x, y = pos.x() / self.escala, pos.y() / self.escala
        for b in self.datos["botones"]:
            if QRectF(b["x"], b["y"], b["w"], b["h"]).contains(x, y):
                return b["id"]
        return None

    def apretar(self, id_boton: str):
        if self.solo and id_boton != self.solo:
            self.evento.emit("senala", "Primero elegí tu compañero", "")
            return
        ahora = time.monotonic()
        self.efectos.tecla()
        self._apretado = (id_boton, ahora + 0.15)
        self._anuncio = config.TITULOS.get(id_boton, id_boton)
        self._anuncio_hasta = ahora + self.DURACION_ANUNCIO

        if id_boton not in self.vistas:
            self.vistas[id_boton] = vista_simple(self._anuncio, "Muy pronto")
            self.pantalla.addWidget(self.vistas[id_boton])
        self.pantalla.setCurrentWidget(self.vistas[id_boton])
        if id_boton in self.modulos:
            self.modulos[id_boton].al_abrir()
        self.update()

    # --- Lo que muestran la pantallita y las luces -----------------------------
    def texto_pantallita(self) -> str:
        if time.monotonic() < self._anuncio_hasta:
            return self._anuncio
        for modulo in self.modulos.values():  # primero, lo urgente (ej.: el Foco corriendo)
            texto = modulo.texto_pantallita()
            if texto:
                return texto
        for modulo in self.modulos.values():  # si no, lo de reposo (ej.: la temperatura)
            texto = modulo.texto_reposo()
            if texto:
                return texto
        return config.TEXTO_REPOSO

    PRIORIDAD_LUCES = ["agenda", "foco", "sonidos", "clima"]   # de lo más urgente a lo menos

    def luces_modulos(self) -> list[bool]:
        ids = self.PRIORIDAD_LUCES + [i for i in self.modulos if i not in self.PRIORIDAD_LUCES]
        for id_modulo in ids:
            modulo = self.modulos.get(id_modulo)
            estado = modulo.luces() if modulo else None
            if estado:
                return estado
        return [False, False, False]

    def estado_animacion(self):
        ahora = time.monotonic()
        t = ahora - self._t0
        luces = [False, False, False]
        lente = 0.0
        retro = False
        if self._fase == "abrir":
            tapa = 1 - suave_entrada(tramo(t, 0.0, 0.35))
            izquierda = rebote_salida(tramo(t, 0.30, 0.70))
            luces = [0.95 + 0.15 * i <= t < 1.25 + 0.15 * i for i in range(3)]
            texto = "Hola" if t < 1.9 else self.texto_pantallita()
            alfa_texto = tramo(t, 1.0, 1.2)
        elif self._fase == "cerrar":
            izquierda = 1 - suave_entrada(tramo(t, 0.0, 0.35))
            tapa = rebote_salida(tramo(t, 0.30, 0.70))
            texto = self.texto_pantallita()
            alfa_texto = 1 - tramo(t, 0.0, 0.15)
        else:
            tapa, izquierda = 0.0, 1.0
            luces = self.luces_modulos()
            texto, alfa_texto = self.texto_pantallita(), 1.0
            en_reposo = ahora >= self._anuncio_hasta and not any(
                m.texto_pantallita() for m in self.modulos.values())
            if en_reposo:
                retro = int(ahora / 5) % 2 == 1      # cada 5 segundos cambia de letra

            g = ahora - self._guardado_t0  # segundos desde que empezó el proceso
            if 0 <= g < 2.2:
                if g < 1.2:
                    texto = self._proceso[0] + "." * (1 + int(g / 0.3) % 3)  # "Guardando...", "Generando QR..."
                    retro = True
                else:
                    texto = self._proceso[1]  # "Listo", "Generado"
                luces = [g < 0.4, 0.4 <= g < 0.8, g >= 0.8]  # rojo, amarillo, verde

            if self._hablando:
                lente = 0.7 + 0.3 * math.sin(ahora * 6)
            elif ahora % 6 < 1.5:                     # en reposo, la lente respira
                lente = 0.25 * math.sin(math.pi * (ahora % 6) / 1.5)
        return tapa, izquierda, lente, luces, texto, alfa_texto, retro

    # --- Dibujo --------------------------------------------------------------
    def paintEvent(self, event):
        tapa, izquierda, lente, luces, texto, alfa_texto, retro = self.estado_animacion()
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p.scale(self.escala, self.escala)

        p.drawPixmap(QPointF(self.bisagra, 0), self.derecha)
        x_a_la_izquierda = self.datos["boton_cerrar"]["x"] < self.bisagra
        if not x_a_la_izquierda:
            self.dibujar_boton_cerrar(p)

        if izquierda > 0.001:
            p.save()
            p.translate(self.bisagra, 0)
            p.scale(izquierda, 1)
            p.translate(-self.bisagra, 0)
            p.drawPixmap(0, 0, self.izquierda)
            self.dibujar_pantallita(p, texto, alfa_texto, retro)
            self.dibujar_boton_apretado(p)
            if x_a_la_izquierda:
                self.dibujar_boton_cerrar(p)
            p.setOpacity(0.45 * max(0.0, 1 - izquierda))
            p.drawPixmap(0, 0, self.izquierda_sombra)
            p.restore()

        if lente > 0:
            l = self.datos["lente"]
            self.brillo(p, l["x"], l["y"], l["r"] * 2.4, QColor(205, 235, 80), lente)
        for encendida, luz in zip(luces, self.datos["luces"]):
            if encendida:
                self.brillo(p, luz["x"], luz["y"], luz["r"] * 2.6, QColor(luz["color"]), 1.0)

        if tapa > 0.001:
            p.save()
            p.translate(self.datos["tapa_x"], 0)
            p.scale(tapa, 1)
            p.drawPixmap(0, 0, self.tapa)
            p.setOpacity(0.45 * max(0.0, 1 - tapa))
            p.drawPixmap(0, 0, self.tapa_sombra)
            p.restore()

    def dibujar_pantallita(self, p: QPainter, texto: str, alfa: float, retro: bool = False):
        from PySide6.QtGui import QFontMetrics  # medidor de texto

        r = self.datos["pantallita"]
        rect = QRectF(r["x"], r["y"], r["w"], r["h"])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1E2733"))
        p.drawRoundedRect(rect, 22, 22)

        # El texto se dibuja en coordenadas reales de la ventana, sin el achique de la imagen
        en_pantalla = p.transform().mapRect(rect)
        p.save()
        p.resetTransform()

        # Aviso corriendo (cartel luminoso): pasa dos veces de derecha a izquierda
        if self._aviso and self._fase == "abierta":
            fuente = QFont(estilos.FUENTE_RETRO)
            fuente.setBold(True)
            fuente.setPixelSize(max(8, int(en_pantalla.height() * 0.34)))
            ancho_texto = QFontMetrics(fuente).horizontalAdvance(self._aviso)
            velocidad = en_pantalla.width() * 0.55  # píxeles por segundo
            recorrido = en_pantalla.width() + ancho_texto
            avance = (time.monotonic() - self._aviso_t0) * velocidad
            if avance < recorrido * 2:
                x = en_pantalla.right() - avance % recorrido
                p.setClipRect(en_pantalla.adjusted(6, 0, -6, 0))  # que no se salga de la pantallita
                p.setFont(fuente)
                p.setPen(QColor("#8FF0A4"))
                p.drawText(QRectF(x, en_pantalla.top(), ancho_texto + 10, en_pantalla.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, self._aviso)
                p.restore()
                return
            self._aviso = ""  # terminó de pasar

        fuente = QFont(estilos.FUENTE_RETRO if retro else estilos.FUENTE)
        fuente.setBold(True)
        tamano = int(en_pantalla.height() * (0.32 if retro else 0.55))
        while tamano > 8:  # achica hasta que entre a lo ancho
            fuente.setPixelSize(tamano)
            if QFontMetrics(fuente).horizontalAdvance(texto) <= en_pantalla.width() * 0.88:
                break
            tamano -= 1
        fuente.setPixelSize(max(8, tamano))
        color = QColor("#8FF0A4" if retro else "#DDF3FA")
        color.setAlphaF(alfa)
        p.setPen(color)
        p.setFont(fuente)
        p.drawText(en_pantalla, Qt.AlignCenter, texto)
        p.restore()

    def dibujar_boton_apretado(self, p: QPainter):
        """Oscurece un instante el botón apretado, como si se hundiera."""
        if not self._apretado or time.monotonic() > self._apretado[1]:
            return
        for b in self.datos["botones"]:
            if b["id"] == self._apretado[0]:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 70))
                p.drawRoundedRect(QRectF(b["x"], b["y"], b["w"], b["h"]), 30, 30)

    def brillo(self, p: QPainter, x, y, radio, color: QColor, intensidad: float):
        grad = QRadialGradient(QPointF(x, y), radio)
        for posicion, alfa in ((0.0, 0.85), (0.4, 0.35), (1.0, 0.0)):
            c = QColor(color)
            c.setAlphaF(alfa * intensidad)
            grad.setColorAt(posicion, c)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(QPointF(x, y), radio, radio)

    # --- Botón de cerrar -------------------------------------------------------------
    def sobre_boton_cerrar(self, pos) -> bool:
        b = self.datos["boton_cerrar"]
        dx = pos.x() / self.escala - b["x"]
        dy = pos.y() / self.escala - b["y"]
        return dx * dx + dy * dy <= b["r"] * b["r"]

    def dibujar_boton_cerrar(self, p: QPainter):
        b = self.datos["boton_cerrar"]
        centro = QPointF(b["x"], b["y"])
        r = b["r"]
        p.setPen(QPen(QColor("#1B2333"), r * 0.12))
        p.setBrush(QColor("#3E5378") if self._sobre_cerrar else QColor("#2B3A55"))
        p.drawEllipse(centro, r, r)
        brazo = r * 0.42
        p.setPen(QPen(QColor("#E8EEF6"), r * 0.2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(centro.x() - brazo, centro.y() - brazo),
                   QPointF(centro.x() + brazo, centro.y() + brazo))
        p.drawLine(QPointF(centro.x() + brazo, centro.y() - brazo),
                   QPointF(centro.x() - brazo, centro.y() + brazo))

    # --- Para el personaje y el director ---------------------------------------------
    def punto_asomarse(self) -> QPoint:
        a = self.datos["asomarse"]
        return self.mapToGlobal(QPoint(int(a["x"] * self.escala), int(a["y"] * self.escala)))

    def zona_que_tapa(self) -> QRect | None:
        if not self.isVisible():
            return None
        g = self.geometry()
        arriba = g.top() + int(self.datos["borde_superior"] * self.escala)
        return QRect(g.left(), arriba, g.width(), g.bottom() - arriba + 1)

    def set_hablando(self, hablando: bool):
        self._hablando = hablando
        self.update()

    def mostrar_guardado(self):
        self.mostrar_proceso("Guardando", "Listo")

    def mostrar_proceso(self, en_proceso: str, listo: str):
        """Muestra en la pantallita un proceso con el semáforo: texto retro y después el resultado."""
        self._proceso = (en_proceso, listo)
        self._guardado_t0 = time.monotonic()
        self.update()

    # --- Mouse -------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._ultimo_arrastre = None
        pos = event.position()
        if self._fase == "abierta":
            if self.sobre_boton_cerrar(pos):
                self.efectos.tecla()
                self.cerrar_pedido.emit()
                return
            boton = self.boton_en(pos)
            if boton:
                self.apretar(boton)
                return
        self._ultimo_arrastre = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        pos = event.position()
        abierta = self._fase == "abierta"
        encima_x = abierta and self.sobre_boton_cerrar(pos)
        clickeable = encima_x or (abierta and self.boton_en(pos) is not None)
        self.setCursor(Qt.PointingHandCursor if clickeable else Qt.ArrowCursor)
        if encima_x != self._sobre_cerrar:
            self._sobre_cerrar = encima_x
            self.update()

        if self._ultimo_arrastre is None:
            return
        actual = event.globalPosition().toPoint()
        delta = actual - self._ultimo_arrastre
        self._ultimo_arrastre = actual
        self.move(self.pos() + delta)
        self.movida.emit(delta)

    def mouseReleaseEvent(self, event):
        self._ultimo_arrastre = None

    def mostrar_aviso(self, texto: str):
        """Hace pasar un mensaje corriendo por la pantallita, como un cartel luminoso."""
        self._aviso = texto
        self._aviso_t0 = time.monotonic()
        self.update()