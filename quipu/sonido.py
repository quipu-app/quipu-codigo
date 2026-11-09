import math
import random
import struct
import sys
import wave

from ajustes import ajustes
from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

import config

FRECUENCIA = 44100   # muestras por segundo (calidad de CD)


# --- Generadores: cada uno devuelve una lista de valores entre -1 y 1 ---------
def _chasquido(t: float, fuerza: float) -> float:
    """Un clic agudo y cortísimo: dos tonos altos que se apagan en milisegundos."""
    tono = math.sin(2 * math.pi * 3200 * t) + 0.6 * math.sin(2 * math.pi * 5100 * t)
    ruido = random.uniform(-1, 1) * math.exp(-t * 1500)
    return fuerza * (tono * math.exp(-t * 900) * 0.6 + ruido * 0.4)


def sonido_clic():
    muestras = []
    for i in range(int(FRECUENCIA * 0.09)):
        t = i / FRECUENCIA
        v = _chasquido(t, 1.0)
        if t > 0.045:                              # el "clac" al soltar, más suave
            v += _chasquido(t - 0.045, 0.45)
        muestras.append(v)
    return muestras


def sonido_suave():
    muestras = []
    for i in range(int(FRECUENCIA * 0.05)):
        t = i / FRECUENCIA
        tono = math.sin(2 * math.pi * 900 * t) + 0.5 * math.sin(2 * math.pi * 1400 * t)
        ruido = random.uniform(-1, 1) * math.exp(-t * 800) * 0.2
        muestras.append(tono * math.exp(-t * 250) * 0.5 + ruido)
    return muestras


def sonido_retro():
    muestras = []
    duracion = 0.035
    for i in range(int(FRECUENCIA * duracion)):
        t = i / FRECUENCIA
        cuadrada = 1.0 if math.sin(2 * math.pi * 1760 * t) >= 0 else -1.0
        envolvente = min(1.0, t / 0.002, (duracion - t) / 0.004)
        muestras.append(cuadrada * envolvente * 0.35)
    return muestras


def sonido_chiflido():
    """Dos notas: una corta y otra que sube, como un chiflido para llamar la atención."""
    notas = [(0.00, 0.11, 1900, 1900),     # (inicio, duración, frecuencia inicial, final)
             (0.16, 0.30, 1700, 2500)]
    muestras = []
    for i in range(int(FRECUENCIA * 0.48)):
        t = i / FRECUENCIA
        v = 0.0
        for inicio, dur, f0, f1 in notas:
            tau = t - inicio
            if 0 <= tau < dur:
                fase = 2 * math.pi * (f0 * tau + (f1 - f0) * tau * tau / (2 * dur))
                envolvente = min(1.0, tau / 0.015, (dur - tau) / 0.03)
                v += math.sin(fase) * envolvente + random.uniform(-1, 1) * 0.03 * envolvente
        muestras.append(v * 0.6)
    return muestras

def sonido_carta():
    """Pasar de carta: un "fiu" cortito que sube."""
    muestras = []
    duracion = 0.12
    fase = 0.0
    for i in range(int(FRECUENCIA * duracion)):
        t = i / FRECUENCIA
        frec = 600 + 900 * (t / duracion)                 # sube de 600 a 1500 Hz
        fase += 2 * math.pi * frec / FRECUENCIA
        envolvente = min(1.0, t / 0.01, (duracion - t) / 0.05)
        muestras.append(math.sin(fase) * envolvente * 0.45)
    return muestras


def sonido_escaneo():
    """El haz del escáner: un zumbido grave y un tono que sube y baja tres veces, como la línea."""
    muestras = []
    duracion = 2.6
    fase = 0.0
    for i in range(int(FRECUENCIA * duracion)):
        t = i / FRECUENCIA
        u = t / duracion
        frec = 520 + 520 * (0.5 - 0.5 * math.cos(u * math.pi * 3))   # sigue al haz
        fase += 2 * math.pi * frec / FRECUENCIA
        zumbido = 0.5 * math.sin(2 * math.pi * 110 * t) + 0.25 * math.sin(2 * math.pi * 220 * t)
        envolvente = min(1.0, t / 0.08, (duracion - t) / 0.15)
        v = (0.55 * math.sin(fase) + 0.35 * zumbido + random.uniform(-1, 1) * 0.04) * envolvente
        muestras.append(v * 0.55)
    return muestras


def sonido_captura():
    """¡Capturado!: dos bips agudos, el segundo más alto."""
    muestras = []
    notas = [(0.00, 0.09, 1320), (0.13, 0.16, 1980)]      # (inicio, duración, frecuencia)
    for i in range(int(FRECUENCIA * 0.32)):
        t = i / FRECUENCIA
        v = 0.0
        for inicio, dur, frec in notas:
            tau = t - inicio
            if 0 <= tau < dur:
                envolvente = min(1.0, tau / 0.005, (dur - tau) / 0.02)
                cuadrada = 1.0 if math.sin(2 * math.pi * frec * tau) >= 0 else -1.0
                v += (0.6 * math.sin(2 * math.pi * frec * tau) + 0.25 * cuadrada) * envolvente
        muestras.append(v * 0.6)
    return muestras


def sonido_codigo():
    """La lluvia de código: blips digitales cortitos, a distintas alturas, durante casi 3 segundos."""
    duracion = 2.9
    total = int(FRECUENCIA * duracion)
    muestras = [0.0] * total
    t = 0.0
    while t < duracion - 0.04:
        frec = random.choice([880, 1175, 1320, 1568, 1760, 2093, 2349])
        largo = random.uniform(0.018, 0.035)
        fuerza = random.uniform(0.25, 0.5) * min(1.0, (duracion - t) / 0.5)   # se apaga al final
        inicio = int(t * FRECUENCIA)
        for j in range(int(largo * FRECUENCIA)):
            if inicio + j >= total:
                break
            tau = j / FRECUENCIA
            cuadrada = 1.0 if math.sin(2 * math.pi * frec * tau) >= 0 else -1.0
            envolvente = min(1.0, tau / 0.002, (largo - tau) / 0.006)
            muestras[inicio + j] += cuadrada * envolvente * fuerza
        t += random.uniform(0.035, 0.07)
    return [max(-0.7, min(0.7, v)) for v in muestras]


def sonido_listo():
    """Listo: una campanita de dos notas que se apaga sola."""
    muestras = []
    notas = [(0.00, 1568), (0.12, 2093)]                  # sol y do agudos
    for i in range(int(FRECUENCIA * 1.1)):
        t = i / FRECUENCIA
        v = 0.0
        for inicio, frec in notas:
            tau = t - inicio
            if tau >= 0:
                caida = math.exp(-tau * 4.5)
                ataque = min(1.0, tau / 0.004)
                v += (math.sin(2 * math.pi * frec * tau)
                      + 0.35 * math.sin(2 * math.pi * frec * 2.76 * tau)) * caida * ataque
        muestras.append(v * 0.35)
    return muestras


EFECTOS_INTERFAZ = {"carta": sonido_carta, "escaneo": sonido_escaneo, "captura": sonido_captura,
                    "codigo": sonido_codigo, "listo": sonido_listo}

SONIDOS_TECLA = {"clic": sonido_clic, "suave": sonido_suave, "retro": sonido_retro}


# --- Archivos WAV ----------------------------------------------------------------
def guardar_wav(ruta, muestras, normalizar=True):
    """Guarda las muestras como WAV mono de 16 bits."""
    if normalizar:
        pico = max(abs(v) for v in muestras) or 1.0
        muestras = [v / pico * 0.8 for v in muestras]
    datos = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in muestras)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(FRECUENCIA)
        archivo.writeframes(datos)

def ruta_sonido(nombre: str, generador):
    """Devuelve la ruta del WAV, generándolo la primera vez."""
    ruta = config.CARPETA_SONIDOS_GENERADOS / f"{nombre}.wav"
    if not ruta.exists():
        guardar_wav(ruta, generador())
    return ruta


def ruta_tecla(nombre: str):
    return ruta_sonido(f"tecla_{nombre}", SONIDOS_TECLA[nombre])


# --- Reproductor -----------------------------------------------------------------
class Efectos:
    """Sonidos cortos de la interfaz. El tipo y el volumen salen de los Ajustes."""

    GENERADORES = {"chiflido": sonido_chiflido,
                   **{f"tecla_{n}": g for n, g in SONIDOS_TECLA.items()},
                   **EFECTOS_INTERFAZ}

    def __init__(self):
        self._usar_winsound = sys.platform == "win32"
        self._padre = QObject()
        self._qt = {}

    def _ruta(self, archivo: str, nivel: int):
        """El WAV de ese sonido a ese volumen, generado la primera vez que se pide."""
        ruta = config.CARPETA_SONIDOS_GENERADOS / f"{archivo}_v{nivel}.wav"
        if not ruta.exists():
            muestras = [v * nivel / 10 for v in self.GENERADORES[archivo]()]
            guardar_wav(ruta, muestras, normalizar=False)
        return ruta

    def reproducir(self, nombre: str):
        a = ajustes()
        if nombre == "tecla":
            tipo = a.get("sonido_teclas")
            if tipo not in SONIDOS_TECLA:          # "ninguno": teclas mudas
                return
            archivo, nivel = f"tecla_{tipo}", a.get("volumen_teclas")
        elif nombre == "chiflido":
            archivo, nivel = "chiflido", a.get("volumen_avisos")
        elif nombre in EFECTOS_INTERFAZ:
            archivo, nivel = nombre, a.get("volumen_teclas")
        else:
            return
        if nivel <= 0:
            return

        ruta = self._ruta(archivo, nivel)
        if self._usar_winsound:
            import winsound
            winsound.PlaySound(str(ruta),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        else:
            efecto = self._qt.get(ruta)
            if efecto is None:
                efecto = QSoundEffect(self._padre)
                efecto.setSource(QUrl.fromLocalFile(str(ruta)))
                self._qt[ruta] = efecto
            efecto.play()

    def tecla(self):
        self.reproducir("tecla")