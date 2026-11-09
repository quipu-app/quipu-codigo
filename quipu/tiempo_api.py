"""Motor del Tiempo: busca ciudades, trae el pronóstico y guarda los ajustes.
Usa Open-Meteo (gratis, sin clave). No depende de Qt, así se puede probar solo."""
import json
import urllib.parse
import urllib.request
from datetime import date

import config

URL_CIUDADES = "https://geocoding-api.open-meteo.com/v1/search"
URL_PRONOSTICO = "https://api.open-meteo.com/v1/forecast"
ARCHIVO_AJUSTES = config.CARPETA_DATOS / "tiempo.json"
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

AJUSTES_INICIALES = {
    "ciudad": "Bahía Blanca", "provincia": "Buenos Aires", "pais": "Argentina",
    "lat": -38.7196, "lon": -62.2724, "unidad": "C", "dias": 5,
}

# Códigos del tiempo (estándar WMO) -> descripción, ícono y reacción del personaje
CODIGOS = {
    0: ("Despejado", "sol", "sol"),
    1: ("Mayormente despejado", "sol", "sol"),
    2: ("Parcialmente nublado", "nube", "nubes"),
    3: ("Nublado", "nube", "nubes"),
    45: ("Niebla", "niebla", "nubes"), 48: ("Niebla con escarcha", "niebla", "frio"),
    51: ("Llovizna leve", "lluvia", "paraguas"), 53: ("Llovizna", "lluvia", "paraguas"),
    55: ("Llovizna intensa", "lluvia", "paraguas"),
    56: ("Llovizna helada", "lluvia", "frio"), 57: ("Llovizna helada intensa", "lluvia", "frio"),
    61: ("Lluvia leve", "lluvia", "paraguas"), 63: ("Lluvia", "lluvia", "paraguas"),
    65: ("Lluvia fuerte", "lluvia", "paraguas"),
    66: ("Lluvia helada", "lluvia", "frio"), 67: ("Lluvia helada fuerte", "lluvia", "frio"),
    71: ("Nevada leve", "nieve", "frio"), 73: ("Nevada", "nieve", "frio"), 75: ("Nevada fuerte", "nieve", "frio"),
    77: ("Granitos de nieve", "nieve", "frio"),
    80: ("Chaparrones leves", "lluvia", "paraguas"), 81: ("Chaparrones", "lluvia", "paraguas"),
    82: ("Chaparrones fuertes", "lluvia", "paraguas"),
    85: ("Chaparrones de nieve", "nieve", "frio"), 86: ("Chaparrones de nieve fuertes", "nieve", "frio"),
    95: ("Tormenta", "tormenta", "paraguas"),
    96: ("Tormenta con granizo", "tormenta", "paraguas"), 99: ("Tormenta con granizo fuerte", "tormenta", "paraguas"),
}


class TiempoError(Exception):
    """Error con un mensaje amable, para mostrar en Quipu."""


def _pedir(url: str, parametros: dict) -> dict:
    """Hace el pedido por internet y devuelve la respuesta ya convertida de JSON."""
    direccion = url + "?" + urllib.parse.urlencode(parametros)
    pedido = urllib.request.Request(direccion, headers={"User-Agent": "Quipu"})
    try:
        with urllib.request.urlopen(pedido, timeout=10) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except Exception as error:
        raise TiempoError("No pude conectarme para ver el tiempo. ¿Hay internet?") from error


def describir(codigo: int) -> dict:
    descripcion, icono, reaccion = CODIGOS.get(codigo, ("Sin datos", "nube", "nubes"))
    return {"descripcion": descripcion, "icono": icono, "reaccion": reaccion}


# --- Ciudades -------------------------------------------------------------------------
def buscar_ciudades(nombre: str, cantidad: int = 5) -> list[dict]:
    """Busca ciudades por nombre. Devuelve varias, porque hay nombres repetidos."""
    if len(nombre.strip()) < 2:
        return []
    datos = _pedir(URL_CIUDADES, {"name": nombre.strip(), "count": cantidad,
                                  "language": "es", "format": "json"})
    return [{
        "ciudad": r["name"], "provincia": r.get("admin1", ""), "pais": r.get("country", ""),
        "lat": r["latitude"], "lon": r["longitude"],
    } for r in datos.get("results", [])]


# --- Pronóstico -------------------------------------------------------------------------
def pronostico(ajustes: dict) -> dict:
    """Trae el tiempo actual y el de los próximos días, según los ajustes."""
    datos = _pedir(URL_PRONOSTICO, {
        "latitude": ajustes["lat"], "longitude": ajustes["lon"],
        "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "fahrenheit" if ajustes["unidad"] == "F" else "celsius",
        "forecast_days": ajustes["dias"], "timezone": "auto",
    })
    actual = datos["current"]
    resultado = {
        "ciudad": ajustes["ciudad"], "unidad": ajustes["unidad"],
        "actual": {"temp": round(actual["temperature_2m"]), "viento": round(actual["wind_speed_10m"]),
                   **describir(actual["weather_code"])},
        "dias": [],
    }
    d = datos["daily"]
    for i, fecha in enumerate(d["time"]):
        dia = date.fromisoformat(fecha)
        resultado["dias"].append({
            "nombre": "Hoy" if i == 0 else DIAS_SEMANA[dia.weekday()],
            "max": round(d["temperature_2m_max"][i]), "min": round(d["temperature_2m_min"][i]),
            "lluvia": d["precipitation_probability_max"][i] or 0,
            **describir(d["weather_code"][i]),
        })
    return resultado


def texto_cartel(p: dict) -> str:
    """El texto que pasa por la pantallita: 'Bahía Blanca · 18° · Parcialmente nublado'."""
    a = p["actual"]
    return f"{p['ciudad']} · {a['temp']}° · {a['descripcion']}"


# --- Ajustes --------------------------------------------------------------------------
def cargar_ajustes() -> dict:
    try:
        return {**AJUSTES_INICIALES, **json.loads(ARCHIVO_AJUSTES.read_text(encoding="utf-8"))}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(AJUSTES_INICIALES)


def guardar_ajustes(ajustes: dict):
    ARCHIVO_AJUSTES.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_AJUSTES.write_text(json.dumps(ajustes, ensure_ascii=False, indent=2), encoding="utf-8")


# --- Prueba desde la terminal ----------------------------------------------------------
if __name__ == "__main__":
    print("Buscando 'Bahía Blanca'...")
    for c in buscar_ciudades("Bahía Blanca"):
        print(f"  {c['ciudad']}, {c['provincia']}, {c['pais']}  ({c['lat']}, {c['lon']})")
    p = pronostico(cargar_ajustes())
    print("\nCartel:", texto_cartel(p))
    print(f"Reacción del personaje: {p['actual']['reaccion']}\n")
    for d in p["dias"]:
        print(f"  {d['nombre']:4} {d['max']:>3}° / {d['min']:>3}°  {d['descripcion']}  (lluvia {d['lluvia']}%)")