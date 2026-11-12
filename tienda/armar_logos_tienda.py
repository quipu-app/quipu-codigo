"""Arma los logos para la ficha de la Microsoft Store a partir de la Q de Quipu."""
from pathlib import Path

from PIL import Image

CARPETA_TIENDA = Path(__file__).resolve().parent
RAIZ = CARPETA_TIENDA.parent
ORIGEN = RAIZ / "quipu" / "assets" / "marca" / "q.png"
DESTINO = CARPETA_TIENDA / "ficha"

COLOR_FONDO = "#0E1834"   # el azul oscuro de la página de Quipu


def centrar(logo: Image.Image, lado: int, fondo) -> Image.Image:
    """Pone el logo en el centro de un cuadrado del tamaño y fondo pedidos."""
    lienzo = Image.new("RGBA", (lado, lado), fondo)
    x = (lado - logo.width) // 2
    y = (lado - logo.height) // 2
    lienzo.paste(logo, (x, y), logo)
    return lienzo


def main():
    logo = Image.open(ORIGEN).convert("RGBA")
    DESTINO.mkdir(exist_ok=True)

    # Ícono de la tienda: la Q en su tamaño real, sobre fondo transparente
    icono = centrar(logo, 300, (0, 0, 0, 0))
    icono.save(DESTINO / "icono_300.png")
    print("  icono_300.png: 300 x 300")

    # Arte de caja: la Q al doble de tamaño, sobre el azul de la marca
    doble = logo.resize((logo.width * 2, logo.height * 2), Image.LANCZOS)
    caja = centrar(doble, 1080, COLOR_FONDO)
    caja.convert("RGB").save(DESTINO / "arte_caja_1080.png")
    print("  arte_caja_1080.png: 1080 x 1080")

    print(f"Listo, quedaron en: {DESTINO}")


if __name__ == "__main__":
    main()