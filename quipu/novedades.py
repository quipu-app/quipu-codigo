"""Novedades de Quipu: mensajes para todos y versiones nuevas, leídos de Firebase."""
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtWidgets import QApplication

import config
import nube
from ajustes import ajustes
from modulos.web import en_segundo_plano

REVISAR_CADA_HORAS = 6
VECES_POR_MENSAJE = 3


def numero(version) -> tuple:
    """'1.10.2' -> (1, 10, 2), para comparar versiones como números y no como texto."""
    return tuple(int(x) for x in str(version).split(".") if x.isdigit())


class Novedades(QObject):
    cambio = Signal()                     # avisa a Ajustes que hay versión nueva o cambió la descarga

    def __init__(self, director):
        super().__init__()
        self.director = director
        self.nueva = None                 # {"version", "descarga"} si hay una versión más nueva
        self.descargando = False
        self._anunciada = False
        reloj = QTimer(self)
        reloj.timeout.connect(self.revisar)
        reloj.start(REVISAR_CADA_HORAS * 3600 * 1000)
        QTimer.singleShot(15000, self.revisar)        # al arrancar, cuando ya se acomodó todo

    def revisar(self):
        en_segundo_plano(nube.novedades, self._llego, self)

    def _llego(self, d, error):
        if error or not d:
            return                                    # sin internet o sin novedades: nada que hacer
        espera = 0
        mensaje = (d.get("mensaje") or "").strip()
        if mensaje:
            a = ajustes()
            veces = a.get("mensaje_veces") if a.get("mensaje_visto") == mensaje else 0
            if veces < VECES_POR_MENSAJE:
                a.set("mensaje_visto", mensaje)
                a.set("mensaje_veces", veces + 1)
                self.anunciar(mensaje)
                espera = 9000                         # que no se pisen dos avisos seguidos
        version = d.get("version", "")
        if d.get("descarga") and numero(version) > numero(config.VERSION):
            self.nueva = {"version": version, "descarga": d["descarga"]}
            self.cambio.emit()
            if not self._anunciada:
                self._anunciada = True
                texto = f"¡Hay una versión nueva de Quipu ({version})! Actualizala desde Ajustes"
                QTimer.singleShot(espera, lambda: self.anunciar(texto))

    def anunciar(self, texto: str):
        self.director.aviso("senala", texto, "chiflido")   # el personaje (o la notificación, si está escondido)
        self.director.consola.mostrar_aviso(texto)          # y el cartel por la pantallita

    def actualizar(self):
        """Baja el instalador nuevo, lo ejecuta en silencio y cierra Quipu para que pueda reemplazarlo."""
        if not self.nueva or self.descargando:
            return
        self.descargando = True
        self.cambio.emit()
        destino = Path(tempfile.gettempdir()) / f"Instalar Quipu {self.nueva['version']}.exe"

        def al_terminar(_, error):
            self.descargando = False
            if error:
                self.director.aviso("piensa", "No pude bajar la actualización. Probá más tarde", "")
                self.cambio.emit()
                return
            QProcess.startDetached(str(destino), ["/SP-", "/SILENT", "/NOCANCEL", "/CLOSEAPPLICATIONS"])
            QTimer.singleShot(500, QApplication.quit)

        en_segundo_plano(lambda: nube.bajar_archivo(self.nueva["descarga"], destino), al_terminar, self)
