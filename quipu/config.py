import os
from pathlib import Path


VERSION = "1.1.0"   # subirla en cada publicación (y también en quipu.iss)

# --- Rutas -------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
CARPETA_PERSONAJES = BASE / "assets" / "personajes"
PERSONAJE_INICIAL = "luna"
ANFITRION = "eric"    # quien recibe en el primer uso, antes de elegir personaje
CARPETA_QUIPU = BASE / "assets" / "consola"
CARPETA_SONIDOS = BASE / "assets" / "sonidos"
CARPETA_AMBIENTE = CARPETA_SONIDOS / "ambiente"
SONIDO_TECLA = "clic"   # "clic", "suave" o "retro"
FOCO_AVISO_FALTA = 0.25   # avisa cuando falta esta fracción del tiempo (0.25 = un cuarto)
CARPETA_FUENTES = BASE / "assets" / "fuentes"
CARPETA_DATOS = Path(os.environ.get("APPDATA", Path.home())) / "Quipu"
CARPETA_SONIDOS_GENERADOS = CARPETA_DATOS / "sonidos"   # los WAV que se arman la primera vez
CARPETA_WEB = BASE / "web"

# --- Tamaño en pantalla --------------------------------------------------------
MODO_INICIAL = "cuerpo"   # "cuerpo" = suelto en el escritorio; "medio" = detrás de Quipu
MARGEN_SUP = 30     # espacio libre arriba para que el salto no se corte
TAMANO_CONSOLA = 0.62  # qué parte del ancho de la pantalla ocupa Quipu abierto (0.55 = 55%)
# --- Ritmo -------------------------------------------------------------------
INTERVALO_MS = 33   # cada cuánto se actualiza (33 ms ≈ 30 veces por segundo)

# --- Mirada ------------------------------------------------------------------
ZONA_FRENTE = 90    # px: con el cursor así de cerca de la cara, mira al frente
QUIETO_SEGUNDOS = 5
DIRECCIONES = [     # 8 miradas en orden de ángulo: 0° = derecha, girando hacia abajo
    "mira_der", "mira_abajo_der", "mira_abajo", "mira_abajo_izq",
    "mira_izq", "mira_arriba_izq", "mira_arriba", "mira_arriba_der",
]

# --- Gestos y acciones -----------------------------------------------------------
DURACION_PARPADEO = 0.14
DURACION_ACCION = 2.2
DURACION_SALTO = 0.45
ALTURA_SALTO = 22
ABURRIDO_SEGUNDOS = 12
PAUSA_ENTRE_OCIOSAS = (15, 30)   # segundos mínimos y máximos entre acciones solas

# --- Globo -------------------------------------------------------------------
GLOBO_FONDO = "#FFFDF6"
GLOBO_TINTA = "#1B2A40"
# --- Módulos de Quipu ------------------------------------------------------------
# id del botón → "archivo.Clase". Los botones sin módulo muestran "Muy pronto".
MODULOS = {
    "foco": "modulos.foco.Foco",
    "notas": "modulos.notas.Notas",
    "clima": "modulos.tiempo.Tiempo",
    "sonidos": "modulos.sonidos.Sonidos",
    "agenda": "modulos.agenda.Agenda",
    "ajustes": "modulos.ajustes.ModuloAjustes",
}
# Nombre que anuncia la pantallita al apretar cada botón
TITULOS = {
    "foco": "Foco", "notas": "Notas", "agenda": "Agenda", "clima": "Tiempo",
    "sonidos": "Sonidos", "ajustes": "Ajustes",
}
TEXTO_REPOSO = "18°"   # lo que muestra la pantallita sin nada activo (después: el clima)

# Frases comunes a todos los personajes, para acciones funcionales
FRASES_COMUNES = {
    "foco_inicio": "¡Arranquemos!",
    "foco_seguimos": "¡Seguimos!",
    "foco_falta_poco": "¡Falta poquito!",
    "foco_fin": "¡Terminaste!",
    "ajustes_hola": "Acá dejamos todo a tu gusto",
    "ajustes_chau": "¡Hasta luego!",
    "ajustes_relevo": "¡Ahí viene el relevo!",
    "ajustes_nombre": "¡Un gusto, {nombre}!",
    "qr_listo": "Listo, ya lo tenés",
    "txt_listo": "Listo, ya lo tenés",
    "imagen_lista": "Listo, ya la agregué",
    "tiempo_paraguas": "¡Llevá paraguas, que llueve!",
    "tiempo_frio": "¡Brr! Hoy abrigate bien",
    "tiempo_sol": "¡Lindo día para salir!",
    "tiempo_nubes": "Está nublado, pero lindo igual",
    "sonidos_hola": "¿Qué querés escuchar?",
    "sonidos_disfruta": "Qué lindo se escucha…",
    "agenda_hola": "A ver qué tenemos…",
    "agenda_guardado": "¡Anotado!",
}

import ctypes
import sys


def _en_tienda() -> bool:
    """True si Quipu está corriendo instalado desde la Microsoft Store (paquete MSIX)."""
    if sys.platform != "win32":
        return False
    try:
        largo = ctypes.c_uint32(0)
        resultado = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(largo), None)
        return resultado != 15700          # 15700 = "este programa no está en un paquete"
    except (AttributeError, OSError):
        return False                       # Windows viejo sin esta función: no es de la Store


EN_TIENDA = _en_tienda()   # se calcula una sola vez, al arrancar Quipu