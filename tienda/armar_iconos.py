"""Arma los íconos que pide la Microsoft Store a partir del logo de Quipu."""
from pathlib import Path

from PIL import Image

CARPETA_TIENDA = Path(__file__).resolve().parent
RAIZ = CARPETA_TIENDA.parent
ORIGEN = RAIZ / "quipu" / "assets" / "marca" / "q.png"
DESTINO = CARPETA_TIENDA / "imagenes"

# nombre del archivo: (lado en píxeles, margen alrededor del logo)
ICONOS = {
    "StoreLogo.png": (50, 0.05),
    "Square44x44Logo.png": (44, 0.0),
    "Square150x150Logo.png": (150, 0.15),
}


def armar(logo: Image.Image, lado: int, margen: float) -> Image.Image:
    """Achica el logo sin deformarlo y lo centra en un cuadrado transparente."""
    espacio = round(lado * (1 - 2 * margen))
    copia = logo.copy()
    copia.thumbnail((espacio, espacio), Image.LANCZOS)
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    x = (lado - copia.width) // 2
    y = (lado - copia.height) // 2
    lienzo.paste(copia, (x, y), copia)
    return lienzo


def main():
    logo = Image.open(ORIGEN).convert("RGBA")
    print(f"Logo original: {logo.width} x {logo.height} píxeles")
    DESTINO.mkdir(exist_ok=True)
    for nombre, (lado, margen) in ICONOS.items():
        armar(logo, lado, margen).save(DESTINO / nombre)
        print(f"  {nombre}: {lado} x {lado}")
    print(f"Listo, quedaron en: {DESTINO}")


if __name__ == "__main__":
    main()