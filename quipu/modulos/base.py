from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget


class Modulo(QObject):
    """Molde que cumple cada función de Quipu."""

    id = ""
    titulo = ""

    # Aviso: (acción del personaje, frase a decir, sonido a reproducir o "")
    evento = Signal(str, str, str)
    guardado = Signal()   # avisa a la consola que se guardó algo
    proceso = Signal(str, str)   # avisa a la pantallita: (texto mientras ocurre, texto al terminar)
    aviso = Signal(str)   # mensaje que pasa corriendo por la pantallita

    def crear_vista(self) -> QWidget:
        """El contenido que se muestra en la pantalla grande."""
        raise NotImplementedError

    def texto_pantallita(self) -> str | None:
        """Texto para la pantallita, o None si este módulo no tiene nada que mostrar."""
        return None

    def luces(self) -> list[bool] | None:
        """Estado de las tres luces [roja, amarilla, verde], o None si no las usa."""
        return None

    def texto_reposo(self) -> str | None:
        """Texto para la pantallita cuando no pasa nada (por ejemplo, la temperatura)."""
        return None

    def al_abrir(self):
        """Se llama cada vez que se aprieta la tecla de este módulo."""