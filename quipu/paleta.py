import json
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage, QPixmap

import config
from ajustes import ajustes

CARPETA_PERSONAJES = Path(__file__).resolve().parent / "assets" / "personajes"
CACHE = config.CARPETA_DATOS / "consolas"
VERSION = 4   # si cambiamos el método de recoloreo, subir este número rehace las imágenes
CSS_TEMA = ""  # los colores del personaje; las páginas lo reciben inyectado (ver modulos/web.py)
LUZ_BASE = (0.299 * 146 + 0.587 * 161 + 0.114 * 189) / 255   # luz del lavanda original


def color_consola(nombre: str | None = None) -> str | None:
    """El color de consola del personaje (o del elegido en Ajustes), o None si no tiene."""
    nombre = nombre or ajustes().get("personaje") or config.PERSONAJE_INICIAL
    try:
        datos = json.loads((CARPETA_PERSONAJES / nombre / "datos.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return datos.get("consola")

def personaje_elegido() -> str:
    """El personaje de Ajustes; si todavía no se eligió ninguno, el anfitrión."""
    return ajustes().get("personaje") or config.ANFITRION


def carpeta_consola():
    """La carpeta de consola del personaje si tiene una propia; si no, la de siempre.
    Devuelve (carpeta, es_propia)."""
    propia = CARPETA_PERSONAJES / personaje_elegido() / "consola"
    if (propia / "quipu.json").exists():
        return propia, True
    return config.CARPETA_QUIPU, False

def _a_numpy(img: QImage, formato, canales: int):
    img = img.convertToFormat(formato)
    ancho, alto = img.width(), img.height()
    crudo = np.frombuffer(img.constBits(), np.uint8).reshape(alto, img.bytesPerLine())
    return crudo[:, :ancho * canales].reshape(alto, ancho, canales).astype(np.float32) / 255


def recolorear(pix: QPixmap, nombre: str, color: str) -> QPixmap:
    """Pinta la carcasa del color pedido usando su máscara, respetando sombras y brillos."""
    archivo = CACHE / f"{nombre}_{color.lstrip('#').upper()}_v{VERSION}.png"
    if archivo.exists():
        guardada = QPixmap(str(archivo))
        if not guardada.isNull():
            return guardada

    mascara = QImage(str(config.CARPETA_QUIPU / f"{nombre}_mascara.png"))
    if mascara.isNull() or mascara.size() != pix.size():
        print(f"Falta la máscara de '{nombre}' (corré crear_mascaras.py): queda el color original")
        return pix

    a = _a_numpy(pix.toImage(), QImage.Format_RGBA8888, 4)
    peso = _a_numpy(mascara, QImage.Format_Grayscale8, 1)
    rgb = a[..., :3]

    # El color nuevo según la luz de cada píxel: más oscuro hacia sombra, más claro hacia blanco
    c = np.array([int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
    # La luz limpia (sin cuadraditos); si no está, se calcula del dibujo tal cual
    limpia = QImage(str(config.CARPETA_QUIPU / f"{nombre}_luz.png"))
    if not limpia.isNull() and limpia.size() == pix.size():
        luz = _a_numpy(limpia, QImage.Format_Grayscale8, 1)
    else:
        luz = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    luz = luz / LUZ_BASE
    nuevo = np.where(luz <= 1, c * luz, c + (1 - c) * np.clip((luz - 1) / (1 / LUZ_BASE - 1), 0, 1))

    a[..., :3] = rgb * (1 - peso) + nuevo * peso

    salida = np.ascontiguousarray((a * 255 + 0.5).astype(np.uint8))
    ancho, alto = salida.shape[1], salida.shape[0]
    resultado = QImage(salida.data, ancho, alto, ancho * 4, QImage.Format_RGBA8888).copy()
    CACHE.mkdir(parents=True, exist_ok=True)
    resultado.save(str(archivo))
    return QPixmap.fromImage(resultado)
COLOR_ORIGINAL = "#92A1BD"   # el lavanda de la consola de siempre


def _a_rgb(color: str):
    return [int(color[i:i + 2], 16) for i in (1, 3, 5)]


def _mezclar(color: str, con: str, cuanto: float) -> str:
    """Mezcla 'color' con 'con' (0 = nada, 1 = todo 'con')."""
    a, b = _a_rgb(color), _a_rgb(con)
    return "#" + "".join(f"{round(x + (y - x) * cuanto):02X}" for x, y in zip(a, b))


def escribir_tema():
    """Guarda web/tema.css con la paleta del personaje elegido, para los botones de las pantallas."""
    base = color_consola() or COLOR_ORIGINAL
    r, g, b = _a_rgb(base)
    luz = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    css = (
        ":root {\n"
        f"  --tema: {base};\n"
        f"  --tema-oscuro: {_mezclar(base, '#000000', 0.35)};\n"
        f"  --tema-muy-oscuro: {_mezclar(base, '#000000', 0.6)};\n"
        f"  --tema-claro: {_mezclar(base, '#FFFFFF', 0.55)};\n"
        f"  --tema-suave: {_mezclar(base, '#FFFFFF', 0.82)};\n"
        f"  --tema-texto: {'#FFFFFF' if luz < 0.6 else '#17324D'};\n"
        "}\n"
    )
    global CSS_TEMA
    CSS_TEMA = css                   # ya no se escribe: cada página lo recibe al cargarse

