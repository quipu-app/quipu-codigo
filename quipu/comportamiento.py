import math
import random
from dataclasses import dataclass

import config


@dataclass
class Estado:
    """Lo que hay que mostrar en un instante dado."""
    gesto: str
    salto: float
    respiro: float
    frase: str | None


class Comportamiento:
    """El cerebro del personaje. No sabe nada de ventanas ni de Qt."""

    def __init__(self, frases, direcciones, acciones_al_tocar, acciones_solo, ahora):
        self.frases = frases
        self.direcciones = direcciones          # las 8 miradas traducidas a esta hoja
        self.acciones_al_tocar = acciones_al_tocar
        self.acciones_solo = acciones_solo

        self._inicio = ahora
        self._ultimo_movimiento = ahora
        self._proximo_parpadeo = ahora + 2.5
        self._fin_parpadeo = 0.0
        self._accion = None
        self._fin_accion = 0.0
        self._inicio_salto = -10.0
        self._proxima_ociosa = ahora + config.ABURRIDO_SEGUNDOS
        self._frase_pedida = None

    # --- Decisiones ------------------------------------------------------------
    def mirada(self, dx: float, dy: float) -> str:
        if math.hypot(dx, dy) < config.ZONA_FRENTE:
            return "mira_frente"
        angulo = math.degrees(math.atan2(dy, dx)) % 360
        return self.direcciones[round(angulo / 45) % 8]

    def hacer(self, accion: str, ahora: float, frase: str | None = None):
        self._accion = accion
        self._fin_accion = ahora + config.DURACION_ACCION
        self._inicio_salto = ahora
        self._frase_pedida = frase

    def tocar(self, ahora: float):
        if self.acciones_al_tocar:
            self.hacer(random.choice(self.acciones_al_tocar), ahora)

    # --- Paso de tiempo --------------------------------------------------------
    def actualizar(self, ahora: float, dx: float, dy: float, cursor_se_movio: bool) -> Estado:
        if cursor_se_movio:
            self._ultimo_movimiento = ahora

        if self._accion and ahora >= self._fin_accion:
            self._accion = None

        quieto = ahora - self._ultimo_movimiento
        if (self.acciones_solo and not self._accion
                and quieto > config.ABURRIDO_SEGUNDOS and ahora >= self._proxima_ociosa):
            self.hacer(random.choice(self.acciones_solo), ahora)
            self._proxima_ociosa = ahora + random.uniform(*config.PAUSA_ENTRE_OCIOSAS)

        if self._accion:
            gesto = self._accion
        else:
            mirada = "mira_frente" if quieto > config.QUIETO_SEGUNDOS else self.mirada(dx, dy)
            if mirada == "mira_frente" and ahora >= self._proximo_parpadeo:
                self._fin_parpadeo = ahora + config.DURACION_PARPADEO
                self._proximo_parpadeo = ahora + random.uniform(2.5, 5.5)
            parpadea = ahora < self._fin_parpadeo and mirada == "mira_frente"
            gesto = "parpadeo" if parpadea else mirada

        respiro = 1 + 0.007 * math.sin(2 * math.pi * (ahora - self._inicio) / 3.2)

        p = (ahora - self._inicio_salto) / config.DURACION_SALTO
        salto = math.sin(math.pi * p) * config.ALTURA_SALTO if 0 <= p < 1 else 0.0

        frase = (self._frase_pedida or self.frases.get(self._accion)) if self._accion else None
        return Estado(gesto, salto, respiro, frase)