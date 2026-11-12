import base64
import json
import sys
import time

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QProcess, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QImage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication

import config
from ajustes import ajustes
from modulos.base import Modulo
from modulos.web import PaginaConConsola, VistaWeb, en_segundo_plano, preparar_qwebchannel
from sincronizacion import google_drive, motor
from paleta import CARPETA_PERSONAJES, personaje_elegido
from sonido import SONIDOS_TECLA, Efectos

CARPETA = config.CARPETA_WEB / "ajustes"
MAXIMO = 10
TIPOS_TECLA = list(SONIDOS_TECLA) + ["ninguno"]
VOLUMENES = {"volumen_teclas": "tecla", "volumen_avisos": "chiflido"}  # ajuste: sonido de prueba
ALTO_CARTA = 340   # alto en píxeles de la imagen que se manda a la carta


# --- Las cartas de los personajes ----------------------------------------------------------
def imagen_carta(carpeta, datos) -> str:
    """El primer cuadro (mirando al frente) del cuerpo del personaje, como imagen para la web."""
    hoja = datos.get("hojas", {}).get("cuerpo")
    if not hoja:
        return ""
    sprite = QImage(str(carpeta / hoja["sprite"]))
    if sprite.isNull():
        return ""
    g = hoja["grilla"]
    n = hoja["cuadros"].get("mira_frente", 0)
    columna, fila = n % g["columnas"], n // g["columnas"]
    cuadro = sprite.copy(columna * g["cuadro_ancho"], fila * g["cuadro_alto"],
                         g["cuadro_ancho"], g["cuadro_alto"])
    cuadro = cuadro.scaledToHeight(ALTO_CARTA, Qt.SmoothTransformation)

    bytes_png = QByteArray()
    buffer = QBuffer(bytes_png)
    buffer.open(QIODevice.WriteOnly)
    cuadro.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(bytes(bytes_png)).decode()


def listar_personajes() -> list[dict]:
    """Todos los personajes que tienen carpeta con datos.json."""
    lista = []
    for carpeta in sorted(CARPETA_PERSONAJES.iterdir()):
        archivo = carpeta / "datos.json"
        if not archivo.exists():
            continue
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if datos.get("anfitrion"):
            continue                     # el anfitrión no se elige: presenta

        lista.append({
            "id": carpeta.name,
            "nombre": datos.get("nombre", carpeta.name.capitalize()),
            "titulo": datos.get("titulo", ""),
            "consola": datos.get("consola", "#93A0BF"),
            "detalle": datos.get("detalle", ""),
            "imagen": imagen_carta(carpeta, datos),
        })
    return lista


class Puente(QObject):
    """Las funciones que Python le presta a la página de Ajustes."""
    cambio = Signal(str)

    def __init__(self, modulo):
        super().__init__()
        self.modulo = modulo
        ajustes().cambio.connect(lambda *_: self.cambio.emit(self.estado()))

    @Slot(result=str)
    def estado(self) -> str:
        a = ajustes()
        return json.dumps({
            "teclas": a.get("volumen_teclas"), "avisos": a.get("volumen_avisos"),
            "tipo": a.get("sonido_teclas"), "tipos": TIPOS_TECLA, "maximo": MAXIMO,
            "personaje": personaje_elegido(),
            "nombre": a.get("nombre"),
            "version": config.VERSION,
            "nueva": (self.modulo.novedades.nueva or {}).get("version", "") if self.modulo.novedades else "",
            "descargando": bool(self.modulo.novedades and self.modulo.novedades.descargando),
            "drive": google_drive.esta_conectado(),
            "sincronizando": self.modulo.sincronizando,
            "ultima_sincro": a.get("ultima_sincronizacion"),
            "sin_conexion": self.modulo.sin_conexion,
        })

    @Slot(result=str)
    def personajes(self) -> str:
        return json.dumps(self.modulo.personajes(), ensure_ascii=False)

    @Slot(str)
    def elegir(self, nombre: str):
        self.modulo.elegir_personaje(nombre)

    @Slot(str)
    def ritual(self, fase: str):
        self.modulo.fase_ritual(fase)

    @Slot(str, int)
    def volumen(self, clave: str, paso: int):
        self.modulo.cambiar_volumen(clave, paso)

    @Slot(str)
    def tipo_tecla(self, tipo: str):
        self.modulo.elegir_tecla(tipo)

    @Slot()
    def abrir_carpeta(self):
        config.CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.CARPETA_DATOS)))

    @Slot()
    def salir(self):
        self.modulo.salir()

    @Slot(str)
    def sonar(self, nombre: str):
        if nombre in ("carta", "tecla"):
            self.modulo.efectos.reproducir(nombre)

    @Slot(str)
    def guardar_nombre(self, nombre: str):
        self.modulo.guardar_nombre(nombre)

    @Slot()
    def conectar_drive(self):
        self.modulo.sincronizar(conectar=True)

    @Slot()
    def sincronizar_ahora(self):
        self.modulo.sincronizar()

    @Slot()
    def desconectar_drive(self):
        self.modulo.desconectar_drive()

    @Slot()
    def actualizar(self):
        if self.modulo.novedades:
            self.modulo.novedades.actualizar()


class ModuloAjustes(Modulo):
    id = "ajustes"
    titulo = "Ajustes"

    def __init__(self):
        super().__init__()
        self.efectos = Efectos()
        self._saliendo = False
        self._cambiando = False
        self._personajes = None    # se arma la primera vez que se pide (las imágenes tardan)
        self._ritual = None              # en qué etapa del ritual estamos, o None
        self.novedades = None            # lo conecta main.py
        self.consola = None              # lo conecta main.py
        self.sincronizando = False
        self._silencioso = False          # True = automática: no muestra nada salvo que lleguen datos
        self.sin_conexion = False
        self._marca = None                # cómo estaban los datos en la última sincronización
        self._marca_inicio = None
        self._cambio_desde = None         # cuándo se notó un cambio todavía sin subir
        self._proxima = time.monotonic() + 10    # la primera, apenas arranca Quipu
        reloj = QTimer(self)
        reloj.timeout.connect(self._revisar_auto)
        reloj.start(5000)                 # cada 5 segundos mira si hay algo para subir

    def personajes(self) -> list[dict]:
        if self._personajes is None:
            self._personajes = listar_personajes()
        return self._personajes

    # --- Acciones ------------------------------------------------------------------------
    def elegir_personaje(self, nombre: str):
        if self._cambiando or nombre == personaje_elegido():
            return
        if nombre not in {p["id"] for p in self.personajes()}:
            return
        primera_vez = ajustes().primer_uso
        ajustes().set("personaje", nombre)
        self._cambiando = True
        if primera_vez:
            self.evento.emit("festeja", "festeja", "")  # Eric: "¡Bienvenido a la familia Quipu!"
        else:
            self.evento.emit("saluda", "ajustes_relevo", "")
        QTimer.singleShot(1800, self.reiniciar)

    FASES = {"escaneo": "ESCANEANDO...", "captura": "¡CAPTURADO!",
             "creando": "CREANDO...", "listo": "LISTO"}

    SONIDO_DE_FASE = {"escaneo": "escaneo", "captura": "captura", "creando": "codigo", "listo": "listo"}

    def fase_ritual(self, fase: str):
        self._ritual = fase if fase in self.FASES else None
        if fase in self.SONIDO_DE_FASE:
            self.efectos.reproducir(self.SONIDO_DE_FASE[fase])

    def luces(self) -> list[bool] | None:
        if self._ritual == "escaneo":
            return [int(time.monotonic() * 4) % 2 == 0, False, False]   # roja parpadeando
        if self._ritual == "captura":
            return [True, True, False]
        if self._ritual == "creando":
            return [False, True, False]
        if self._ritual == "listo" or self._cambiando:
            return [False, False, True]
        if self.sincronizando and not self._silencioso:          # semáforo dando vueltas
            paso = int(time.monotonic() * 2.5) % 3
            return [paso == 0, paso == 1, paso == 2]
        if self.sin_conexion:                                    # amarilla: sin internet, reintenta solo
            return [False, True, False]
        return None

    def reiniciar(self):
        """Abre un Quipu nuevo (que ya lee el personaje elegido) y cierra este."""
        QProcess.startDetached(sys.executable, sys.argv)
        QApplication.quit()

    def cambiar_volumen(self, clave: str, paso: int):
        if clave not in VOLUMENES:
            return
        a = ajustes()
        a.set(clave, max(0, min(MAXIMO, a.get(clave) + paso)))
        self.efectos.reproducir(VOLUMENES[clave])     # para escuchar cómo quedó

    def elegir_tecla(self, tipo: str):
        if tipo in TIPOS_TECLA:
            ajustes().set("sonido_teclas", tipo)
            self.efectos.tecla()

    LARGO_NOMBRE = 20

    def guardar_nombre(self, nombre: str):
        nombre = " ".join(nombre.split())[:self.LARGO_NOMBRE]    # sin espacios de más
        if not nombre or nombre == ajustes().get("nombre"):
            return
        ajustes().set("nombre", nombre)
        ajustes().set("nombre_cambiado", time.time())
        self.evento.emit("saluda", "ajustes_nombre", "")

    def salir(self):
        if self._saliendo:
            return
        self._saliendo = True
        self.evento.emit("saluda", "ajustes_chau", "")
        QTimer.singleShot(2000, self.salir_sincronizando)    # tiempo para la despedida, y sube lo pendiente

    # --- Sincronización con Google Drive --------------------------------------------------
    ESPERA_TRAS_CAMBIO = 8        # segundos después de guardar algo
    CADA_CUANTO = 10 * 60         # además, cada 10 minutos (para traer lo que hiciste en el celu)
    REINTENTO = 2 * 60            # si falló (sin internet), reintenta a los 2 minutos

    def _avisar_pagina(self):
        if getattr(self, "puente", None):
            self.puente.cambio.emit(self.puente.estado())

    def sincronizar(self, conectar: bool = False, silencioso: bool = False):
        """Sincroniza en segundo plano. Con conectar=True, abre el navegador para entrar con Google."""
        if self.sincronizando:
            return
        self.sincronizando = True
        self._silencioso = silencioso
        self._marca_inicio = motor.marca_local()
        a = ajustes()
        perfil = {"nombre": a.get("nombre") or "", "nombre_cambiado": a.get("nombre_cambiado") or 0}
        self._avisar_pagina()
        en_segundo_plano(lambda: motor.sincronizar(permitir_navegador=conectar, perfil=perfil),
                         lambda resultado, error: self._sincro_termino(resultado, error, conectar, silencioso),
                         self)

    def _sincro_termino(self, resultado, error, conectar: bool, silencioso: bool):
        self.sincronizando = False
        self._silencioso = False
        estado = (resultado or {}).get("estado")
        ahora = time.monotonic()
        if estado == "listo":
            self.sin_conexion = False
            self._marca = self._marca_inicio       # lo que cambie desde ahora se sube en la próxima
            self._cambio_desde = None
            self._proxima = ahora + self.CADA_CUANTO
            perfil = resultado.get("perfil")
            if perfil:                             # el nombre cambió en otro aparato
                ajustes().set("nombre", perfil.get("nombre") or "")
                ajustes().set("nombre_cambiado", perfil.get("nombre_cambiado") or 0)
            ajustes().set("ultima_sincronizacion", time.time())
            bajados = sum(resultado["bajados"].values())
            if not silencioso or bajados:
                self.proceso.emit("Sincronizando", "Listo")
            if conectar:
                self.evento.emit("festeja", "¡Listo! Tus datos ya viajan con vos", "")
            if bajados:
                self._refrescar_pantallas()
        else:
            self._proxima = ahora + self.REINTENTO
            if error or estado is None:
                print(f"Sincronización: {error}", flush=True)
                self.sin_conexion = True
                if not silencioso:
                    self.evento.emit("piensa", "No pude sincronizar. ¿Hay internet?", "")
            elif not silencioso and estado == "sin_conectar":
                self.evento.emit("piensa", "No pude conectarme con Google", "")
            elif not silencioso and estado == "formato_nuevo":
                self.evento.emit("piensa", "Actualizá Quipu para poder sincronizar", "")
        self._avisar_pagina()

    def _refrescar_pantallas(self):
        """Si llegaron datos de otro aparato, Notas y Agenda se vuelven a cargar."""
        if not self.consola:
            return
        for id_modulo in ("notas", "agenda"):
            vista = getattr(self.consola.modulos.get(id_modulo), "vista", None)
            if vista:
                vista.reload()

    def _editando(self) -> bool:
        """True si Notas o Agenda están en pantalla: ahí no se sincroniza, para no pisar lo que escribís."""
        c = self.consola
        if not c or not c.abierta:
            return False
        actual = c.pantalla.currentWidget()
        return actual is not None and actual in (c.vistas.get("notas"), c.vistas.get("agenda"))

    def _revisar_auto(self):
        """Cada 5 segundos: si algo cambió (o tocó la vuelta de cada 10 minutos), sincroniza."""
        if self.sincronizando or self._saliendo or not google_drive.esta_conectado():
            return
        ahora = time.monotonic()
        if self._marca is not None and self._cambio_desde is None and motor.marca_local() != self._marca:
            self._cambio_desde = ahora
        cambio_listo = self._cambio_desde is not None and ahora - self._cambio_desde >= self.ESPERA_TRAS_CAMBIO
        if (cambio_listo or ahora >= self._proxima) and not self._editando():
            self.sincronizar(silencioso=True)

    def salir_sincronizando(self):
        """Antes de cerrar Quipu, sube lo pendiente (esperando 10 segundos como máximo)."""
        if google_drive.esta_conectado() and (self._marca is None or motor.marca_local() != self._marca):
            self.sincronizar(silencioso=True)
        self._limite_salida = time.monotonic() + 10
        self._esperar_y_salir()

    def _esperar_y_salir(self):
        if self.sincronizando and time.monotonic() < self._limite_salida:
            QTimer.singleShot(300, self._esperar_y_salir)
            return
        QApplication.quit()

    def desconectar_drive(self):
        google_drive.desconectar()
        self.sin_conexion = False
        self.evento.emit("sonrie", "Listo, me desconecté de Google", "")
        self._avisar_pagina()

    def al_abrir(self):
        self.evento.emit("sonrie", "ajustes_hola", "")

    # --- La pantallita -------------------------------------------------------------------
    def texto_pantallita(self) -> str | None:
        if self._cambiando:
            return "CAMBIANDO"
        if self._ritual:
            return self.FASES[self._ritual]
        if self.novedades and self.novedades.descargando:
            return "DESCARGANDO"
        if self.sincronizando and not self._silencioso:
            return "SINCRONIZANDO"
        return "HASTA LUEGO" if self._saliendo else None

    # --- La pantalla grande --------------------------------------------------------------
    def crear_vista(self):
        preparar_qwebchannel(CARPETA)
        self.vista = VistaWeb()
        self.pagina = PaginaConConsola("ajustes", self.vista)
        self.vista.setPage(self.pagina)
        self.pagina.setBackgroundColor(Qt.transparent)

        self.puente = Puente(self)
        self.canal = QWebChannel(self.pagina)
        self.canal.registerObject("puente", self.puente)
        self.pagina.setWebChannel(self.canal)

        self.vista.setUrl(QUrl.fromLocalFile(str(CARPETA / "ajustes.html")))
        return self.vista