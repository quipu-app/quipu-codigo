"""Herramienta de una sola vez: arma las máscaras de la carcasa de Quipu.
Una máscara es una imagen en grises: blanco = carcasa (se recolorea), negro = no se toca.
Hay que volver a correrla solo si cambian las imágenes de la consola."""
import json

import numpy as np
from PIL import Image
from scipy import ndimage

import config


def tono_saturacion_brillo(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    hay = d > 1e-6
    dd = np.where(hay, d, 1)
    rc, gc, bc = (mx - r) / dd, (mx - g) / dd, (mx - b) / dd
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    h = np.where(hay, (h / 6) % 1, 0) * 360
    s = np.where(mx > 0, d / np.where(mx > 0, mx, 1), 0)
    return h, s, mx


def crear_mascara(ruta):
    a = np.asarray(Image.open(ruta).convert("RGBA")).astype(np.float32) / 255
    rgb, alfa = a[..., :3], a[..., 3]
    h, s, v = tono_saturacion_brillo(rgb)
    luz = rgb @ np.array([0.299, 0.587, 0.114], np.float32)

    # 1. Las líneas negras del dibujo separan el dibujo en zonas cerradas
    linea = (luz < 0.2) | (alfa < 0.5)
    zonas, n = ndimage.label(~linea)
    ids = np.arange(1, n + 1)

    # 2. Cada zona se juzga entera por su color típico: si es lavanda, es carcasa
    th = ndimage.median(h, zonas, ids)
    ts = ndimage.median(s, zonas, ids)
    tv = ndimage.median(v, zonas, ids)
    tam = ndimage.sum(np.ones_like(h), zonas, ids)
    es_carcasa = (th >= 204) & (th <= 236) & (ts >= 0.2) & (ts <= 0.5) & (tv >= 0.42) & (tam > 30)
    elegidas = np.zeros(n + 1, bool)
    elegidas[1:] = es_carcasa
    m = elegidas[zonas]

    # 3. Proteger lo que tiene otro color dentro de la carcasa (lente, luces), con su brillo
    otro = ((h < 185) | (h > 250)) & (s > 0.15)
    etiquetas, cuantos = ndimage.label(otro)
    grandes = np.zeros(cuantos + 1, bool)
    grandes[1:] = ndimage.sum(otro, etiquetas, np.arange(1, cuantos + 1)) > 400
    otro = ndimage.binary_fill_holes(ndimage.binary_dilation(grandes[etiquetas], iterations=5))
    m &= ~otro

    # 4. Las esquinas grises de goma quedan grises
    gris = (s < 0.22) & (v < 0.55) & (h < 214)
    gris = ndimage.binary_closing(ndimage.binary_opening(gris, iterations=2), iterations=3)
    m &= ~gris

    # 5. Sumar el borde suavizado de las líneas y suavizar apenas el contorno
    m |= ndimage.binary_dilation(m, iterations=3) & linea & (alfa > 0.5)
    suave = ndimage.gaussian_filter(m.astype(np.float32), 0.8)
    return Image.fromarray((suave * 255 + 0.5).astype(np.uint8), "L")

def crear_luz_limpia(ruta):
    """La luz de cada píxel, sin los cuadraditos de compresión pero con los detalles nítidos."""
    a = np.asarray(Image.open(ruta).convert("RGB")).astype(np.float32) / 255
    luz = a @ np.array([0.299, 0.587, 0.114], np.float32)
    suave = ndimage.gaussian_filter(ndimage.median_filter(luz, size=13), 1.0)
    # Donde la diferencia es chica es ruido: se usa la versión suave.
    # Donde es grande es un detalle (letras, bordes): se deja el original.
    ruido = np.clip((0.07 - np.abs(luz - suave)) / 0.03, 0, 1)
    limpia = luz * (1 - ruido) + suave * ruido
    return Image.fromarray((limpia * 255 + 0.5).astype(np.uint8), "L")

if __name__ == "__main__":
    carpeta = config.CARPETA_QUIPU
    datos = json.loads((carpeta / "quipu.json").read_text(encoding="utf-8"))
    for clave in ("interior", "tapa"):
        origen = carpeta / datos[clave]
        for sufijo, crear in (("mascara", crear_mascara), ("luz", crear_luz_limpia)):
            destino = carpeta / f"{clave}_{sufijo}.png"
            crear(origen).save(destino)
            print("Lista:", destino)