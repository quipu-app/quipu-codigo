import json
import time

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel

import config
from ambiente import NIVELES, SONIDOS, Ambiente
from modulos.base import Modulo
from modulos.web import PaginaConConsola, VistaWeb, preparar_qwebchannel

CARPETA = config.CARPETA_WEB / "sonidos"
VOLUMEN_EN_PANTALLITA = 1.5   # segundos que se ven las barritas después de cambiar el volumen


class Puente(QObject):
    """Las funciones que Python le presta a la página de Sonidos."""
    cambio = Signal(str)   # avisa a la página cuando cambia algo (prendido, volumen, temporizador)

    def __init__(self, modulo):
        super().__init__()
        self.modulo = modulo
        modulo.ambiente.cambio.connect(lambda: self.cambio.emit(self.estado()))

    @Slot(result=str)
    def estado(self) -> str:
        a = self.modulo.ambiente
        return json.dumps({
            "sonidos": [{"clave": c, "nombre": n, "on": c in a.encendidos, "nivel": a.niveles[c]}
                        for c, n in SONIDOS.items()],
            "general": a.general, "maximo": NIVELES, "minutos": a.minutos_restantes(),
        }, ensure_ascii=False)

    @Slot(str)
    def alternar(self, clave: str):
        self.modulo.alternar(clave)

    @Slot(str, int)
    def nivel(self, clave: str, paso: int):
        self.modulo.ambiente.cambiar_nivel(clave, paso)
        self.modulo.mostrar_volumen(self.modulo.ambiente.niveles[clave])

    @Slot(int)
    def general(self, paso: int):
        self.modulo.ambiente.cambiar_general(paso)
        self.modulo.mostrar_volumen(self.modulo.ambiente.general)

    @Slot(int)
    def temporizador(self, minutos: int):
        self.modulo.ambiente.temporizador(minutos)

    @Slot()
    def apagar_todo(self):
        self.modulo.ambiente.apagar_todo()


class Sonidos(Modulo):
    id = "sonidos"
    titulo = "Sonidos"

    def __init__(self):
        super().__init__()
        self.ambiente = Ambiente(self)       # vive aunque cierres la consola: sigue sonando
        self._volumen = None                 # (nivel, hasta cuándo se muestra)

    # --- Acciones con reacción del personaje ---------------------------------------------
    def alternar(self, clave: str):
        prendiendo = clave not in self.ambiente.encendidos
        self.ambiente.alternar(clave)
        if prendiendo:
            self.evento.emit("disfruta", "sonidos_disfruta", "")
        if self.ambiente.encendidos:
            self.aviso.emit(self.ambiente.texto())   # "♪ Lluvia + Fogón" pasando por la pantallita

    def mostrar_volumen(self, nivel: int):
        self._volumen = (nivel, time.monotonic() + VOLUMEN_EN_PANTALLITA)

    def al_abrir(self):
        self.evento.emit("escucha", "sonidos_hola", "")

    # --- La pantallita y las luces -------------------------------------------------------
    def texto_pantallita(self) -> str | None:
        if self._volumen and time.monotonic() < self._volumen[1]:
            llenas = round(self._volumen[0] / 2)
            return "VOL " + "▮" * llenas + "▯" * (5 - llenas)
        return None

    def luces(self) -> list[bool] | None:
        if not self.ambiente.encendidos:
            return None
        return [False, False, int(time.monotonic() / 0.8) % 2 == 0]   # verde latiendo

    # --- La pantalla grande --------------------------------------------------------------
    def crear_vista(self):
        preparar_qwebchannel(CARPETA)
        self.vista = VistaWeb()
        self.pagina = PaginaConConsola("sonidos", self.vista)
        self.vista.setPage(self.pagina)
        self.pagina.setBackgroundColor(Qt.transparent)

        self.puente = Puente(self)
        self.canal = QWebChannel(self.pagina)
        self.canal.registerObject("puente", self.puente)
        self.pagina.setWebChannel(self.canal)

        self.vista.setUrl(QUrl.fromLocalFile(str(CARPETA / "sonidos.html")))
        return self.vista