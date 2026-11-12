import json

from PySide6.QtCore import QObject, Signal

import config

# Valores con los que arranca Quipu la primera vez.
# Para sumar un ajuste nuevo en el futuro, alcanza con agregarlo acá.
VALORES_INICIALES = {
    "version": 1,
    "personaje": None,         # None = todavía no se eligió (primer uso)
    "volumen_teclas": 7,       # de 0 a 10
    "volumen_avisos": 3,       # el chiflido, de 0 a 10
    "sonido_teclas": "clic",   # "clic", "suave", "retro" o "ninguno"
    "nombre": "",  # cómo te ven los demás en las notas compartidas
    "mensaje_visto": "",       # el último mensaje de novedades que se mostró
    "mensaje_veces": 0,        # cuántas veces se mostró (hasta 3)
    "personaje_escondido": False,  # True = solo la Q en la bandeja, sin personaje en el escritorio
    "ultima_sincronizacion": 0,    # cuándo se sincronizó con Drive por última vez (0 = nunca)
    "nombre_cambiado": 0,          # cuándo se cambió el nombre (viaja con el nombre a Drive)
}


class Ajustes(QObject):
    """Lee y guarda los ajustes de Quipu en ajustes.json, dentro de la carpeta de datos."""

    cambio = Signal(str, object)  # avisa qué ajuste cambió y su valor nuevo

    def __init__(self):
        super().__init__()
        self.ruta = config.CARPETA_DATOS / "ajustes.json"
        self._datos = dict(VALORES_INICIALES)
        self._cargar()

    def _cargar(self):
        if not self.ruta.exists():
            return
        try:
            guardados = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Si el archivo se rompió, lo apartamos y arrancamos con los valores iniciales
            self.ruta.replace(self.ruta.with_name("ajustes.roto.json"))
            return
        self._datos.update({c: v for c, v in guardados.items() if c in VALORES_INICIALES})

    def get(self, clave: str):
        return self._datos.get(clave, VALORES_INICIALES.get(clave))

    def set(self, clave: str, valor):
        if clave not in VALORES_INICIALES:
            raise KeyError(f"'{clave}' no es un ajuste de Quipu")
        if self._datos.get(clave) == valor:
            return
        self._datos[clave] = valor
        self._guardar()
        self.cambio.emit(clave, valor)

    def _guardar(self):
        config.CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_name("ajustes.tmp")
        temporal.write_text(json.dumps(self._datos, ensure_ascii=False, indent=2), encoding="utf-8")
        temporal.replace(self.ruta)

    @property
    def primer_uso(self) -> bool:
        return self.get("personaje") is None


_instancia = None


def ajustes() -> Ajustes:
    """Devuelve siempre los mismos Ajustes, para que toda la app comparta uno solo."""
    global _instancia
    if _instancia is None:
        _instancia = Ajustes()
    return _instancia