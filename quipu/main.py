import os
import sys
if not getattr(sys, "frozen", False):   # solo al programar; en el instalador quedan apagadas
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"   # permite inspeccionar las páginas de Quipu desde Chrome
import sys
import config
import estilos

from paleta import escribir_tema, personaje_elegido
from PySide6 import QtWebEngineWidgets  # noqa: F401 (tiene que cargarse antes de QApplication)
from PySide6.QtWidgets import QApplication
from consola import Consola
from director import Director
from bandeja import Bandeja
from novedades import Novedades
from personaje import Personaje
from ajustes import ajustes
from paleta import personaje_elegido


def main():
    app = QApplication(sys.argv)   # una sola vez, siempre al principio
    estilos.cargar_fuentes()
    escribir_tema()              # los botones de las pantallas, con el color del personaje
    primer_uso = ajustes().primer_uso
    personaje = Personaje(personaje_elegido(), config.MODO_INICIAL)
    consola = Consola()
    director = Director(personaje, consola)

    pantalla = app.primaryScreen().availableGeometry()
    personaje.move(
        pantalla.right() - personaje.width() - 40,
        pantalla.bottom() - personaje.height() - 20,
    )
    personaje.show()
    app.setQuitOnLastWindowClosed(False)   # Quipu sigue vivo aunque no se vea ninguna ventana
    bandeja = Bandeja(director)            # la Q junto al reloj, con su menú
    novedades = Novedades(director)        # mensajes y versiones nuevas desde Firebase
    modulo_ajustes = consola.modulos["ajustes"]
    modulo_ajustes.novedades = novedades
    modulo_ajustes.consola = consola
    novedades.cambio.connect(lambda: modulo_ajustes.puente.cambio.emit(modulo_ajustes.puente.estado()))

    if primer_uso:
        director.bienvenida()      # Eric recibe y lleva a elegir compañero

    sys.exit(app.exec())


if __name__ == "__main__":
    main()