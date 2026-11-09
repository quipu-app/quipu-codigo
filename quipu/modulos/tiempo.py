import json

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel

import config
import tiempo_api
from modulos.base import Modulo
from modulos.web import PaginaConConsola, VistaWeb, en_segundo_plano, preparar_qwebchannel

CARPETA = config.CARPETA_WEB / "tiempo"
ACTUALIZAR_CADA_MIN = 30   # cada cuánto se consulta el tiempo
CARTEL_CADA_MIN = 5        # cada cuánto pasa el cartel por la pantallita


class Puente(QObject):
    """Las funciones que Python le presta a la página del Tiempo."""
    pronostico_listo = Signal(str)   # avisa a la página cuando llega el pronóstico

    def __init__(self, modulo):
        super().__init__()
        self.modulo = modulo

    @Slot(result=str)
    def ajustes(self) -> str:
        return json.dumps(tiempo_api.cargar_ajustes(), ensure_ascii=False)

    @Slot(str, result=str)
    def buscar(self, nombre: str) -> str:
        try:
            return json.dumps({"ok": True, "ciudades": tiempo_api.buscar_ciudades(nombre)}, ensure_ascii=False)
        except tiempo_api.TiempoError as error:
            return json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False)

    @Slot(str)
    def guardar(self, datos: str):
        tiempo_api.guardar_ajustes(json.loads(datos))
        self.modulo.guardado.emit()                      # "Guardando…" con el semáforo
        self.modulo.actualizar()

    @Slot()
    def pedir_pronostico(self):
        if self.modulo.datos:                            # mostramos lo último al instante...
            self.pronostico_listo.emit(json.dumps({"ok": True, **self.modulo.datos}, ensure_ascii=False))
        self.modulo.actualizar()                         # ...y pedimos lo más nuevo


class Tiempo(Modulo):
    id = "clima"
    titulo = "Tiempo"

    def __init__(self):
        super().__init__()
        self.datos = None          # el último pronóstico que llegó
        self.puente = None

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.actualizar)
        self.reloj.start(ACTUALIZAR_CADA_MIN * 60 * 1000)
        self.reloj_cartel = QTimer(self)
        self.reloj_cartel.timeout.connect(self.pasar_cartel)
        self.reloj_cartel.start(CARTEL_CADA_MIN * 60 * 1000)
        QTimer.singleShot(2000, self.actualizar)        # la primera consulta, al arrancar Quipu

    # --- Consultar el tiempo -----------------------------------------------------------
    def actualizar(self):
        ajustes = tiempo_api.cargar_ajustes()

        def al_terminar(resultado, error):
            if error:
                mensaje = str(error) if isinstance(error, tiempo_api.TiempoError) \
                    else "Algo salió mal al consultar el tiempo."
                respuesta = {"ok": False, "error": mensaje}
            else:
                self.datos = resultado
                respuesta = {"ok": True, **resultado}
            if self.puente:
                self.puente.pronostico_listo.emit(json.dumps(respuesta, ensure_ascii=False))

        en_segundo_plano(lambda: tiempo_api.pronostico(ajustes), al_terminar, self)

    # --- La pantallita -----------------------------------------------------------------
    def texto_reposo(self) -> str | None:
        return f"{self.datos['actual']['temp']}°" if self.datos else None

    def pasar_cartel(self):
        if self.datos:
            self.aviso.emit(tiempo_api.texto_cartel(self.datos))

    def luces(self) -> list[bool] | None:
        """Amarilla (atención) si llueve o hace mucho frío."""
        if self.datos and self.reaccion() in ("paraguas", "frio"):
            return [False, True, False]
        return None

    # --- La reacción del personaje -------------------------------------------------------
    def reaccion(self) -> str:
        """Elige la reacción según el tiempo actual: paraguas, frío, sol o nubes."""
        a = self.datos["actual"]
        celsius = a["temp"] if self.datos["unidad"] == "C" else (a["temp"] - 32) * 5 / 9
        if a["reaccion"] == "paraguas":
            return "paraguas"
        if celsius <= 8:
            return "frio"
        if a["reaccion"] == "sol" and celsius >= 15:
            return "sol"
        return a["reaccion"]

    def al_abrir(self):
        if not self.datos:
            return
        r = self.reaccion()
        self.evento.emit(r, f"tiempo_{r}", "")       # gesto (si el personaje lo tiene) y frase
        self.pasar_cartel()

    # --- La pantalla grande --------------------------------------------------------------
    def crear_vista(self):
        preparar_qwebchannel(CARPETA)
        self.vista = VistaWeb()
        self.pagina = PaginaConConsola("tiempo", self.vista)
        self.vista.setPage(self.pagina)
        self.pagina.setBackgroundColor(Qt.transparent)

        self.puente = Puente(self)
        self.canal = QWebChannel(self.pagina)
        self.canal.registerObject("puente", self.puente)
        self.pagina.setWebChannel(self.canal)

        self.vista.setUrl(QUrl.fromLocalFile(str(CARPETA / "tiempo.html")))
        return self.vista