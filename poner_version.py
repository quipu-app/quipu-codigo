"""Pone el mismo número de versión en todos los lugares donde figura.
Uso: python poner_version.py 1.1.0"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
    raise SystemExit("Uso: python poner_version.py 1.1.0")
version = sys.argv[1]
a, b, c = version.split(".")


def cambiar(ruta, reemplazos):
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8-sig")
    nuevo = texto
    for patron, reemplazo in reemplazos:
        nuevo, cantidad = re.subn(patron, reemplazo, nuevo)
        if cantidad == 0:
            raise SystemExit(f"  ERROR: en {ruta} no encontré {patron}")
    ruta.write_text(nuevo, encoding="utf-8")
    print(f"  {ruta}: listo")


cambiar("quipu/config.py", [(r'VERSION = "[\d.]+"', f'VERSION = "{version}"')])
cambiar("quipu.iss", [(r"AppVersion=[\d.]+", f"AppVersion={version}"),
                      (r"VersionInfoVersion=[\d.]+", f"VersionInfoVersion={version}")])
cambiar("info_version.txt", [(r"filevers=\([\d, ]+\)", f"filevers=({a}, {b}, {c}, 0)"),
                             (r"prodvers=\([\d, ]+\)", f"prodvers=({a}, {b}, {c}, 0)"),
                             (r"'FileVersion', '[\d.]+'", f"'FileVersion', '{version}'"),
                             (r"'ProductVersion', '[\d.]+'", f"'ProductVersion', '{version}'")])
cambiar("tienda/AppxManifest.xml", [(r'(<Identity[^>]*?\sVersion=")[\d.]+(")', rf"\g<1>{version}.0\g<2>")])
print(f"\nVersión {version} puesta en todos lados.")