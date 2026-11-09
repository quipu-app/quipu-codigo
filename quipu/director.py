import random

from PySide6.QtCore import QPoint, QTimer

import config
from ajustes import ajustes

from consola import Consola
from personaje import Personaje


class Director:
    """Coordina al personaje y a la consola. Ninguno de los dos conoce al otro."""

    def __init__(self, personaje: Personaje, consola: Consola):
        self.personaje = personaje
        self.consola = consola

        personaje.tocado.connect(self.personaje_tocado)
        consola.cerrar_pedido.connect(self.cerrar_consola)
        consola.movida.connect(self.consola_movida)
        personaje.oclusor = consola.zona_que_tapa
        self.lugar_original = None
        consola.evento.connect(self.aviso)
        personaje.hablando.connect(consola.set_hablando)
        self.en_bienvenida = False

    def personaje_tocado(self):
        if self.personaje.saltando:
            return
        if self.consola.abierta:
            self.personaje.reaccionar()
            self.consola.raise_()          # que la consola siga adelante
        else:
            self.abrir_consola()

    def abrir_consola(self):
        self.lugar_original = self.personaje.pie()  # recordamos dónde estaba parado
        self.consola.abrir()
        ajuste = self.personaje.datos["hojas"]["medio"].get("ajuste_asomarse", 0)
        destino = self.consola.punto_asomarse() + QPoint(0, ajuste)
        self.personaje.saltar(destino, "medio", al_terminar=self.consola.raise_)

    def cerrar_consola(self):
        if self.en_bienvenida:
            self.personaje.decir("piensa", "Primero elegí tu compañero")
            return
        if self.personaje.saltando or not self.consola.abierta:
            return
        self.consola.cerrar()
        self.personaje.saltar(self.lugar_original, "cuerpo")

    def consola_movida(self, delta: QPoint):
        if self.personaje.modo == "medio" and not self.personaje.saltando:
            self.personaje.move(self.personaje.pos() + delta)

    def aviso(self, accion: str, frase: str, sonido: str):
        bandeja = getattr(self, "bandeja", None)
        if bandeja and not self.personaje.isVisible():
            bandeja.avisar(self.texto_frase(frase))   # personaje escondido: notificación de Windows
        else:
            self.personaje.decir(accion, frase)  # primero el personaje: que nunca se pierda el aviso
        if sonido:
            try:
                self.consola.efectos.reproducir(sonido)
            except Exception as error:
                print(f"No pude reproducir el sonido '{sonido}': {error}", flush=True)

    def texto_frase(self, frase: str) -> str:
        texto = self.personaje.datos.get("frases", {}).get(frase) or config.FRASES_COMUNES.get(frase) or frase
        if isinstance(texto, list):
            texto = random.choice(texto)
        return texto.replace("{nombre}", ajustes().get("nombre") or "")

    # --- La bienvenida (primer uso) --------------------------------------------------
    def bienvenida(self):
        """Eric se presenta, abre Quipu en Ajustes y espera a que elijan compañero."""
        self.en_bienvenida = True
        self.consola.solo = "ajustes"         # mientras tanto, las demás teclas no abren nada
        pasos = [                             # (segundos desde el arranque, qué pasa)
            (0.8, self.abrir_consola),
            (2.0, lambda: self.consola.apretar("ajustes")),
            (2.8, lambda: self.personaje.decir("saluda", "saluda")),
            (6.5, lambda: self.personaje.decir("presenta", "presenta")),
            (10.5, lambda: self.personaje.decir("senala", "Escribí tu nombre acá abajo, así te conozco")),
            (15.0, lambda: self.personaje.decir("senala", "senala")),
        ]
        for segundos, accion in pasos:
            QTimer.singleShot(int(segundos * 1000), accion)