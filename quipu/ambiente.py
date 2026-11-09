"""Motor de sonidos ambientes: varios a la vez, en loop, con volumen, fundidos y temporizador."""
import time
import json

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QSoundEffect

import config

SONIDOS = {"lluvia": "Lluvia", "rio": "Río", "fogon": "Fogón", "viento": "Viento", "campo": "Campo"}
NIVELES = 10          # cada volumen va de 0 a 10
FUNDIDO_SEG = 1.5     # cuánto tarda en subir o bajar al prender o apagar
TIC_MS = 50           # cada cuánto se actualiza el volumen durante un fundido


class Ambiente(QObject):
    cambio = Signal()   # avisa cuando algo cambió (para la pantalla y la pantallita)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.niveles = {clave: 6 for clave in SONIDOS}   # volumen de cada sonido
        self.general = 7                                 # volumen general
        self.encendidos: set[str] = set()
        self.fin_temporizador = None                     # hora en que se apaga todo, o None

        self._cargar()
        self.cambio.connect(self._guardar)   # cada cambio queda guardado

        self.efectos = {}
        self.actual = {clave: 0.0 for clave in SONIDOS}  # volumen que suena ahora (durante el fundido)
        for clave in SONIDOS:
            efecto = QSoundEffect(self)
            efecto.setSource(QUrl.fromLocalFile(str(config.CARPETA_AMBIENTE / f"{clave}.wav")))
            efecto.setLoopCount(QSoundEffect.Loop.Infinite.value)  # repetir sin fin
            efecto.setVolume(0.0)
            self.efectos[clave] = efecto

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self._tic)
        self.reloj.start(TIC_MS)

    # --- Recordar la mezcla entre sesiones ------------------------------------------------
    def _archivo(self):
        return config.CARPETA_DATOS / "sonidos.json"

    def _cargar(self):
        try:
            datos = json.loads(self._archivo().read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return                                     # primera vez: quedan los valores iniciales
        for clave, nivel in datos.get("niveles", {}).items():
            if clave in self.niveles:
                self.niveles[clave] = max(0, min(NIVELES, int(nivel)))
        self.general = max(0, min(NIVELES, int(datos.get("general", self.general))))

    def _guardar(self):
        self._archivo().parent.mkdir(parents=True, exist_ok=True)
        self._archivo().write_text(json.dumps({"niveles": self.niveles, "general": self.general}),
                                   encoding="utf-8")

    # --- Lo que se puede hacer ------------------------------------------------------------
    def alternar(self, clave: str):
        if clave in self.encendidos:
            self.encendidos.discard(clave)
        else:
            self.encendidos.add(clave)
            if not self.efectos[clave].isPlaying():
                self.efectos[clave].play()
        self.cambio.emit()

    def apagar_todo(self):
        self.encendidos.clear()
        self.fin_temporizador = None
        self.cambio.emit()

    def cambiar_nivel(self, clave: str, paso: int):
        self.niveles[clave] = max(0, min(NIVELES, self.niveles[clave] + paso))
        self.cambio.emit()

    def cambiar_general(self, paso: int):
        self.general = max(0, min(NIVELES, self.general + paso))
        self.cambio.emit()

    def temporizador(self, minutos: int):
        """Apaga todo en 'minutos' (0 = sin temporizador)."""
        self.fin_temporizador = time.monotonic() + minutos * 60 if minutos else None
        self.cambio.emit()

    # --- Lo que se puede consultar ----------------------------------------------------------
    def sonando(self) -> list[str]:
        return [clave for clave in SONIDOS if clave in self.encendidos]

    def texto(self) -> str:
        """Para la pantallita: '♪ Lluvia + Fogón'."""
        return "♪ " + " + ".join(SONIDOS[c] for c in self.sonando()) if self.encendidos else ""

    def minutos_restantes(self) -> int | None:
        if self.fin_temporizador is None:
            return None
        return max(0, round((self.fin_temporizador - time.monotonic()) / 60))

    # --- El reloj: fundidos y temporizador -----------------------------------------------------
    def objetivo(self, clave: str) -> float:
        if clave not in self.encendidos:
            return 0.0
        # Al cuadrado: el oído percibe el volumen así, y los pasos suenan parejos
        return (self.niveles[clave] / NIVELES) ** 2 * (self.general / NIVELES) ** 2

    def _tic(self):
        if self.fin_temporizador and time.monotonic() >= self.fin_temporizador:
            self.apagar_todo()
        paso = TIC_MS / 1000 / FUNDIDO_SEG
        for clave, efecto in self.efectos.items():
            meta = self.objetivo(clave)
            v = self.actual[clave]
            v = min(meta, v + paso) if v < meta else max(meta, v - paso)
            if v != self.actual[clave]:
                self.actual[clave] = v
                efecto.setVolume(v)
            if v == 0 and clave not in self.encendidos and efecto.isPlaying():
                efecto.stop()                    # terminó de bajar: lo frenamos del todo


# --- Prueba desde la terminal -------------------------------------------------------------
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    a = Ambiente()
    print("Prendo lluvia y fogón...")
    a.alternar("lluvia")
    a.alternar("fogon")
    QTimer.singleShot(5000, lambda: (print("Subo el fogón al máximo..."), a.cambiar_nivel("fogon", +4)))
    QTimer.singleShot(9000, lambda: (print("Sumo el campo..."), a.alternar("campo")))
    QTimer.singleShot(14000, lambda: (print("Apago todo (baja de a poco)..."), a.apagar_todo()))
    QTimer.singleShot(17000, app.quit)
    print("En la pantallita diría:", a.texto())
    app.exec()