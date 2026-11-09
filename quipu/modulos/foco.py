import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget,
)

import config
import estilos
from modulos.base import Modulo
from paleta import COLOR_ORIGINAL, color_consola
from tecla import Tecla

def color_botones() -> str:
    """El color del personaje elegido; si no tiene (bienvenida), el lavanda de la consola."""
    return color_consola() or COLOR_ORIGINAL


class Temporizador:
    """La lógica pura del foco, sin nada de Qt (reutilizable en Android)."""

    def __init__(self, minutos: int = 25):
        self.duracion = minutos * 60
        self.estado = "listo"            # listo, corriendo, pausa, terminado
        self._restante = self.duracion
        self._fin = None
        self.terminado_en = None

    def restante(self, ahora: float) -> float:
        if self.estado == "corriendo":
            return max(0.0, self._fin - ahora)
        return self._restante

    def elegir(self, minutos: int):
        if self.estado in ("listo", "terminado"):
            self.duracion = minutos * 60
            self.reiniciar()

    def iniciar(self, ahora: float):
        if self.estado == "terminado":
            self.reiniciar()
        if self.estado in ("listo", "pausa"):
            self._fin = ahora + self._restante
            self.estado = "corriendo"

    def pausar(self, ahora: float):
        if self.estado == "corriendo":
            self._restante = self.restante(ahora)
            self.estado = "pausa"

    def reiniciar(self):
        self._restante = self.duracion
        self._fin = None
        self.estado = "listo"

    def verificar(self, ahora: float) -> bool:
        """Devuelve True justo en el momento en que termina."""
        if self.estado == "corriendo" and ahora >= self._fin:
            self.estado = "terminado"
            self._restante = 0
            self.terminado_en = ahora
            return True
        return False


def mmss(segundos: float) -> str:
    s = int(segundos + 0.999)            # redondeo hacia arriba: nunca muestra 00:00 antes de tiempo
    return f"{s // 60:02d}:{s % 60:02d}"


class Foco(Modulo):
    id = "foco"
    titulo = "Foco"

    def __init__(self):
        super().__init__()
        self.temp = Temporizador(25)
        self.vista = None
        self._aviso_dado = False         # ¿ya dijo "te falta poco" en este foco?
        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.tic)
        self.reloj.start(250)            # corre siempre, aunque Quipu esté cerrado

    # --- Reloj propio ---------------------------------------------------------------
    def tic(self):
        ahora = time.monotonic()
        t = self.temp

        # Aviso cuando falta poco
        if (t.estado == "corriendo" and not self._aviso_dado
                and t.restante(ahora) <= t.duracion * config.FOCO_AVISO_FALTA):
            self._aviso_dado = True
            self.evento.emit("sonrie", "foco_falta_poco", "")

        if t.verificar(ahora):
            self.evento.emit("festeja", "foco_fin", "chiflido")

        if self.vista:
            self.refrescar()

    def principal(self):
        ahora = time.monotonic()
        estado = self.temp.estado
        if estado == "corriendo":
            self.temp.pausar(ahora)
        else:
            self.temp.iniciar(ahora)
            if estado == "pausa":
                self.evento.emit("sonrie", "foco_seguimos", "")
            else:
                self._aviso_dado = False  # foco nuevo: el aviso vuelve a estar disponible
                self.evento.emit("senala", "foco_inicio", "chiflido")
        self.refrescar()

    # --- Lo que la consola le pregunta -----------------------------------------
    def texto_pantallita(self):
        ahora = time.monotonic()
        if self.temp.estado in ("corriendo", "pausa"):
            return mmss(self.temp.restante(ahora))
        if self.temp.estado == "terminado" and ahora - self.temp.terminado_en < 8:
            return "¡Listo!"
        return None

    def luces(self):
        ahora = time.monotonic()
        t = self.temp
        if t.estado == "corriendo":
            falta_poco = t.restante(ahora) <= t.duracion * config.FOCO_AVISO_FALTA
            return [False, falta_poco and int(ahora * 2) % 2 == 0, True]
        if t.estado == "pausa":
            return [False, True, False]
        if t.estado == "terminado" and ahora - t.terminado_en < 8:
            return [int(ahora * 6) % 3 == i for i in range(3)]   # festejo: corren de una a otra
        return None

    # --- La pantalla grande ------------------------------------------------------
    def crear_vista(self) -> QWidget:
        v = QWidget()
        v.setObjectName("vista")
        v.setAttribute(Qt.WA_StyledBackground)
        v.setStyleSheet(estilos.qss_pantalla("foco"))
        color = color_botones()          # los botones, con el color del personaje

        titulo = QLabel("Foco")
        titulo.setObjectName("titulo")
        self.lbl_tiempo = QLabel(mmss(self.temp.duracion))
        self.lbl_tiempo.setObjectName("tiempo")
        self.lbl_tiempo.setAlignment(Qt.AlignCenter)

        self.barra = QProgressBar()
        self.barra.setRange(0, 1000)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(estilos.px(6))

        # Teclas de minutos: solo una puede quedar marcada (hundida)
        fila_min = QHBoxLayout()
        fila_min.setSpacing(estilos.px(6))
        self.grupo_min = QButtonGroup(v)
        for minutos in (15, 25, 45):
            b = Tecla(f"{minutos} min", color)
            b.setCheckable(True)
            b.setChecked(minutos == 25)
            b.clicked.connect(lambda _=False, m=minutos: self.temp.elegir(m))
            self.grupo_min.addButton(b)
            fila_min.addWidget(b)

        # Teclas de control
        fila_ctrl = QHBoxLayout()
        fila_ctrl.setSpacing(estilos.px(6))
        self.btn_principal = Tecla("Iniciar", color)
        self.btn_principal.clicked.connect(self.principal)
        btn_reiniciar = Tecla("Reiniciar", color)
        btn_reiniciar.clicked.connect(self.temp.reiniciar)
        fila_ctrl.addWidget(self.btn_principal, 2)
        fila_ctrl.addWidget(btn_reiniciar, 1)

        caja = QVBoxLayout(v)
        caja.setContentsMargins(estilos.px(10), estilos.px(8), estilos.px(10), estilos.px(10))
        caja.setSpacing(estilos.px(6))
        caja.addWidget(titulo)
        caja.addWidget(self.lbl_tiempo)
        caja.addWidget(self.barra)
        caja.addLayout(fila_min)
        caja.addLayout(fila_ctrl)

        self.vista = v
        self.refrescar()
        return v

    def refrescar(self):
        t = self.temp
        restante = t.restante(time.monotonic())
        self.lbl_tiempo.setText(mmss(restante))
        self.barra.setValue(int(1000 * (1 - restante / t.duracion)))
        self.btn_principal.setText({
            "listo": "Iniciar", "corriendo": "Pausar",
            "pausa": "Seguir", "terminado": "Otra vez",
        }[t.estado])
        libre = t.estado in ("listo", "terminado")
        for b in self.grupo_min.buttons():
            b.setEnabled(libre)

    def refrescar(self):
        t = self.temp
        restante = t.restante(time.monotonic())
        self.lbl_tiempo.setText(mmss(restante))
        self.barra.setValue(int(1000 * (1 - restante / t.duracion)))
        self.btn_principal.setText({
            "listo": "Iniciar", "corriendo": "Pausar",
            "pausa": "Seguir", "terminado": "Otra vez",
        }[t.estado])
        libre = t.estado in ("listo", "terminado")
        for b in self.grupo_min.buttons():
            b.setEnabled(libre)