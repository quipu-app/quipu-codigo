"""Piezas comunes para los módulos que usan el mini navegador (Notas, Tiempo, ...)."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QTimer
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView

ANCHO_DISENO = 340   # ancho en píxeles para el que están pensadas las páginas
_trabajadores = ThreadPoolExecutor(max_workers=2)


def preparar_qwebchannel(carpeta: Path):
    """Copia qwebchannel.js desde dentro de Qt a la carpeta de la página (una sola vez)."""
    destino = carpeta / "qwebchannel.js"
    if destino.exists():
        return
    archivo = QFile(":/qtwebchannel/qwebchannel.js")
    if archivo.open(QIODevice.ReadOnly):
        destino.write_bytes(bytes(archivo.readAll()))
        archivo.close()


def en_segundo_plano(tarea, al_terminar, padre):
    """Ejecuta 'tarea' sin congelar Quipu y, cuando termina, llama a 'al_terminar(resultado, error)'."""
    futuro = _trabajadores.submit(tarea)
    reloj = QTimer(padre)

    def revisar():
        if futuro.done():
            reloj.stop()
            reloj.deleteLater()
            error = futuro.exception()
            al_terminar(None if error else futuro.result(), error)

    reloj.timeout.connect(revisar)
    reloj.start(100)


class PaginaConConsola(QWebEnginePage):
    """Página que muestra en la terminal los mensajes y errores del JavaScript."""

    def __init__(self, nombre: str, padre=None):
        super().__init__(padre)
        self.nombre = nombre
        import paleta                    # acá adentro: al crear la página, el tema ya está calculado
        if paleta.CSS_TEMA:
            guion = QWebEngineScript()
            guion.setName("tema")
            guion.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
            guion.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            guion.setSourceCode("(() => { const s = document.createElement('style'); s.textContent = "
                                + json.dumps(paleta.CSS_TEMA) + "; document.head.appendChild(s); })();")
            self.scripts().insert(guion)

    def javaScriptConsoleMessage(self, nivel, mensaje, linea, origen):
        print(f"[{self.nombre}.js:{linea}] {mensaje}", flush=True)


class VistaWeb(QWebEngineView):
    """Mini navegador que ajusta el zoom para que la página siempre ocupe todo el ancho."""

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self.width() > 0:
            self.setZoomFactor(self.width() / ANCHO_DISENO)