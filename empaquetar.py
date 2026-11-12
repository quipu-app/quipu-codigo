import os
import sys
from pathlib import Path

import PyInstaller.__main__

raiz = Path("quipu")
sep = os.pathsep                       # en Windows, ";" separa origen y destino en --add-data

# Controles antes de armar
if not (raiz / "firebase.json").exists():
    raise SystemExit("Falta quipu/firebase.json: sin él, Colaborar no anda en el programa.")
if not (raiz / "sincronizacion" / "credenciales_google.json").exists():
    raise SystemExit("Falta quipu/sincronizacion/credenciales_google.json: sin él, no se puede conectar Google Drive.")
sobrantes = list(raiz.rglob("*.antes")) + list(raiz.rglob("*.antes2"))
if sobrantes:
    print(f"Aviso: hay {len(sobrantes)} archivos .antes que van a viajar dentro del programa.\n")

# 1. Que "modulos" sea un paquete de verdad
init = raiz / "modulos" / "__init__.py"
if not init.exists():
    init.write_text("", encoding="utf-8")
    print("Creé quipu/modulos/__init__.py")

# 2. La lista exacta de módulos, leída de config.MODULOS
sys.path.insert(0, str(raiz))
import config  # noqa: E402

ocultos = {"modulos", "modulos.base", "modulos.web"}
ocultos |= {ruta.rsplit(".", 1)[0] for ruta in config.MODULOS.values()}
print("Módulos que se incluyen:", ", ".join(sorted(ocultos)))

argumentos = [
    str(raiz / "main.py"),
    "--name", "Quipu",
    "--icon", str(raiz / "assets" / "marca" / "q.ico"),   # la Q en el .exe y en la barra de tareas
    "--windowed",                                    # sin ventana negra de consola
    "--noconfirm", "--clean",                        # rearma desde cero cada vez
    "--paths", str(raiz),                            # para que encuentre config, consola, director...
    "--add-data", f"{raiz / 'assets'}{sep}assets",   # personajes, consolas, sonidos y fuentes
    "--add-data", f"{raiz / 'web'}{sep}web",         # las pantallas HTML
    "--add-data", f"{raiz / 'firebase.json'}{sep}.", # la conexión con Firebase
    "--add-data", f"{raiz / 'sincronizacion' / 'credenciales_google.json'}{sep}sincronizacion",  # Google Drive
    "--collect-data", "googleapiclient",             # las descripciones de las APIs de Google
    "--hidden-import", "sincronizacion.google_drive",
    "--hidden-import", "sincronizacion.motor",
]
for modulo in sorted(ocultos):
    argumentos += ["--hidden-import", modulo]

PyInstaller.__main__.run(argumentos)
print("\nListo: el programa quedó en dist\\Quipu\\Quipu.exe")