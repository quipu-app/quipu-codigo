import json
import time
from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel

import agenda_datos
import config
from modulos.base import Modulo
from modulos.web import PaginaConConsola, VistaWeb, preparar_qwebchannel

CARPETA = config.CARPETA_WEB / "agenda"


class Puente(QObject):
    """Las funciones que Python le presta a la página de la Agenda."""
    pregunta_cambio = Signal(str)   # avisa a la página cuando aparece o se responde una pregunta

    def __init__(self, modulo):
        super().__init__()
        self.modulo = modulo
        self.datos = modulo.datos

    @Slot(int, int, result=str)
    def mes(self, anio: int, mes: int) -> str:
        """Los colores de los eventos de cada día del mes (para los puntitos)."""
        puntos = {}
        for o in self.datos.del_mes(anio, mes):
            colores = puntos.setdefault(o["dia"], [])
            if o["color"] not in colores and len(colores) < 3:
                colores.append(o["color"])
        return json.dumps({"titulo": f"{agenda_datos.MESES[mes - 1]} {anio}", "puntos": puntos,
                           "hoy": date.today().isoformat()}, ensure_ascii=False)

    @Slot(str, result=str)
    def dia(self, fecha: str) -> str:
        """Los eventos de un día, con el nombre del día para el título."""
        d = date.fromisoformat(fecha)
        eventos = [{"id": o["id"], "titulo": o["titulo"], "hora": o["hora"], "color": o["color"],
                    "repite": o["repetir"] != "no"} for o in self.datos.del_dia(d)]
        return json.dumps({"nombre": agenda_datos.nombre_dia(d), "eventos": eventos}, ensure_ascii=False)

    @Slot(int, result=str)
    def evento(self, evento_id: int) -> str:
        return json.dumps(dict(self.datos.evento(evento_id)), ensure_ascii=False)

    @Slot(str, result=int)
    def guardar(self, datos: str) -> int:
        d = json.loads(datos)
        if not d["titulo"].strip():
            return -1
        evento_id = self.datos.guardar(d.get("id"), d["titulo"], d["fecha"], d.get("hora", ""),
                                       d.get("color", "#E5484D"), d.get("aviso_min", 10), d.get("repetir", "no"))
        self.modulo.guardado.emit()                                   # "Guardando…" con el semáforo
        self.modulo.evento.emit("tacha", "agenda_guardado", "")       # el personaje tacha en su libretita
        return evento_id

    @Slot(int)
    def borrar(self, evento_id: int):
        self.datos.borrar(evento_id)

    @Slot(result=str)
    def pregunta(self) -> str:
        """El evento que espera respuesta, o "" si no hay ninguno."""
        return self.modulo.pregunta_json()

    @Slot(str)
    def responder(self, respuesta: str):
        self.modulo.responder(respuesta)


REVISAR_CADA_SEG = 20      # cada cuánto se fija si hay que avisar algo
CARTEL_CADA_MIN = 5        # cada cuánto pasa lo próximo del día por la pantallita
PREGUNTAR_DESPUES_MIN = 30 # minutos después de la hora del evento para preguntar si se hizo


class Agenda(Modulo):
    id = "agenda"
    titulo = "Agenda"

    def __init__(self):
        super().__init__()
        self.datos = agenda_datos.Agenda()
        self.avisados: set[tuple] = set()     # (id, día) de lo que ya se avisó, para no repetir
        self.pendiente = None                 # el evento avisado que todavía no empezó
        self.pregunta = None                  # el evento que ya pasó y espera "¿se hizo?"
        self.puente = None

        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self.revisar)
        self.reloj.start(REVISAR_CADA_SEG * 1000)
        self.reloj_cartel = QTimer(self)
        self.reloj_cartel.timeout.connect(self.pasar_cartel)
        self.reloj_cartel.start(CARTEL_CADA_MIN * 60 * 1000)
        QTimer.singleShot(3000, self.revisar)   # la primera revisión, al arrancar Quipu

    # --- Los avisos -----------------------------------------------------------------------
    def revisar(self):
        ahora = datetime.now()
        if not self.pregunta:
            self.pregunta = self.datos.para_preguntar(ahora, PREGUNTAR_DESPUES_MIN)
            if self.pregunta:
                self.preguntar()
        if self.pendiente and ahora >= self.pendiente["inicio"]:
            self.pendiente = None                       # ya empezó: se apaga la luz roja
        for o in self.datos.proximos(ahora, horas=2):
            clave = (o["id"], o["dia"])
            if o["avisar_en"] and o["avisar_en"] <= ahora and clave not in self.avisados:
                self.avisados.add(clave)
                self.pendiente = o
                self.avisar(o, ahora)
                break                                   # de a un aviso por vez

    def avisar(self, o, ahora: datetime):
        minutos = max(1, round((o["inicio"] - ahora).total_seconds() / 60))
        frase = f"¡En {minutos} minutos tenés {o['titulo']}!"
        self.evento.emit("campana", frase, "chiflido")   # gesto, frase y sonido
        self.aviso.emit(f"{o['hora']} · {o['titulo']}")

    # --- ¿Se hizo? ------------------------------------------------------------------------
    def preguntar(self):
        o = self.pregunta
        self.evento.emit("senala", f"¿Hiciste: {o['titulo']}?", "chiflido")
        self.aviso.emit(f"¿Hiciste: {o['titulo']}?")
        self.avisar_pagina()

    def pregunta_json(self) -> str:
        if not self.pregunta:
            return ""
        o = self.pregunta
        return json.dumps({"id": o["id"], "dia": o["dia"], "titulo": o["titulo"], "hora": o["hora"],
                           "color": o["color"], "repite": o["repetir"] != "no"}, ensure_ascii=False)

    def avisar_pagina(self):
        if self.puente:
            self.puente.pregunta_cambio.emit(self.pregunta_json())

    def responder(self, respuesta: str):
        o = self.pregunta
        if not o:
            return
        self.datos.responder(o["id"], o["dia"], respuesta)
        self.pregunta = None
        accion, frase = {
            "si": ("festeja", "¡Bien ahí!"),
            "no": ("sonrie", "Bueno, otra vez será"),
            "reprogramar": ("senala", "Elegí el nuevo día y la hora"),
        }.get(respuesta, ("sonrie", "¡Anotado!"))
        self.evento.emit(accion, frase, "")
        self.avisar_pagina()

    def pasar_cartel(self):
        """Hace pasar lo próximo de hoy por la pantallita."""
        ahora = datetime.now()
        for o in self.datos.del_dia(date.today()):
            if not o["hora"]:
                self.aviso.emit(f"Hoy · {o['titulo']}")
                return
            if datetime.fromisoformat(f"{o['dia']}T{o['hora']}") >= ahora:
                self.aviso.emit(f"Hoy {o['hora']} · {o['titulo']}")
                return

    # --- La pantallita y las luces ---------------------------------------------------------
    def texto_pantallita(self) -> str | None:
        return self.pendiente["hora"] if self.pendiente else None

    def luces(self) -> list[bool] | None:
        if self.pendiente:
            return [int(time.monotonic()) % 2 == 0, False, False]   # roja titilando: ya viene
        if self.pregunta:
            return [True, False, False]                             # roja fija: espera tu respuesta
        return None

    # --- Al abrir y la pantalla grande ---------------------------------------------------
    def al_abrir(self):
        self.evento.emit("calendario", "agenda_hola", "")
        self.pasar_cartel()

    def crear_vista(self):
        preparar_qwebchannel(CARPETA)
        self.vista = VistaWeb()
        self.pagina = PaginaConConsola("agenda", self.vista)
        self.vista.setPage(self.pagina)
        self.pagina.setBackgroundColor(Qt.transparent)

        self.puente = Puente(self)
        self.canal = QWebChannel(self.pagina)
        self.canal.registerObject("puente", self.puente)
        self.pagina.setWebChannel(self.canal)

        self.vista.setUrl(QUrl.fromLocalFile(str(CARPETA / "agenda.html")))
        return self.vista