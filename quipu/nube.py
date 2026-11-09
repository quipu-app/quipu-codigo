"""Las notas compartidas: hablan con Firebase (Firestore) usando solo lo que trae Python."""
import json
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import config

ALFABETO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"   # sin 0/O, 1/I/L: fáciles de dictar sin confundirse
SESION = config.CARPETA_DATOS / "sesion_nube.json"
_candado = threading.Lock()                     # que dos pedidos a la vez no pisen la sesión
_cfg = None


class NubeError(Exception):
    pass


def _config() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = json.loads((config.BASE / "firebase.json").read_text(encoding="utf-8"))
    return _cfg


def _pedir(metodo, url, datos=None, token=None, formulario=False):
    """Hace un pedido a Firebase y devuelve (código, respuesta)."""
    if datos is None:
        cuerpo, tipo = None, "application/json"
    elif formulario:
        cuerpo, tipo = urllib.parse.urlencode(datos).encode(), "application/x-www-form-urlencoded"
    else:
        cuerpo, tipo = json.dumps(datos).encode(), "application/json"
    req = urllib.request.Request(url, data=cuerpo, method=metodo)
    req.add_header("Content-Type", tipo)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except urllib.error.URLError:
        raise NubeError("Sin conexión a internet")


def _sesion() -> dict:
    """La identidad anónima de este Quipu: la renueva si venció, o pide una nueva."""
    with _candado:
        clave = _config()["apiKey"]
        s = json.loads(SESION.read_text(encoding="utf-8")) if SESION.exists() else None
        if s and s["expira"] > time.time() + 60:
            return s
        r = None
        if s:                                                   # renovar la que ya tenemos
            codigo, r = _pedir("POST", f"https://securetoken.googleapis.com/v1/token?key={clave}",
                               {"grant_type": "refresh_token", "refresh_token": s["refresco"]}, formulario=True)
            if codigo == 200:
                s = {"token": r["id_token"], "refresco": r["refresh_token"], "uid": r["user_id"],
                     "expira": time.time() + int(r["expires_in"])}
            else:
                r = None
        if r is None:                                           # entrar por primera vez
            codigo, r = _pedir("POST", f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={clave}",
                               {"returnSecureToken": True})
            if codigo != 200:
                raise NubeError("No pude conectarme con la nube")
            s = {"token": r["idToken"], "refresco": r["refreshToken"], "uid": r["localId"],
                 "expira": time.time() + int(r["expiresIn"])}
        SESION.parent.mkdir(parents=True, exist_ok=True)
        SESION.write_text(json.dumps(s), encoding="utf-8")
        return s


def _url(codigo: str) -> str:
    return (f"https://firestore.googleapis.com/v1/projects/{_config()['projectId']}"
            f"/databases/(default)/documents/compartidas/{codigo}")


# --- Códigos ------------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """'k7m4-qx2p ' -> 'K7M4QX2P'."""
    return "".join(c for c in texto.upper() if c.isalnum())


def codigo_libre() -> str:
    for _ in range(5):
        codigo = "".join(secrets.choice(ALFABETO) for _ in range(8))
        if bajar(codigo) is None:
            return codigo
    raise NubeError("No pude generar un código, probá de nuevo")


# --- Subir y bajar ------------------------------------------------------------------------
def subir(codigo: str, titulo: str, html: str, texto: str) -> float:
    """Sube la nota y devuelve el momento en que quedó guardada."""
    s = _sesion()
    cambiado = time.time()
    campos = {"fields": {
        "titulo": {"stringValue": titulo or ""}, "html": {"stringValue": html or ""},
        "texto": {"stringValue": texto or ""}, "cambiado": {"doubleValue": cambiado},
        "autor": {"stringValue": s["uid"]},
    }}
    estado, r = _pedir("PATCH", _url(codigo), campos, s["token"])
    if estado == 403:
        raise NubeError("La nota es muy pesada para compartir (¿muchas fotos?)")
    if estado != 200:
        raise NubeError(f"La nube respondió {estado}")
    return cambiado


def bajar(codigo: str) -> dict | None:
    """La nota compartida con ese código, o None si no existe."""
    s = _sesion()
    estado, r = _pedir("GET", _url(codigo), token=s["token"])
    if estado == 404:
        return None
    if estado != 200:
        raise NubeError(f"La nube respondió {estado}")
    d = {k: next(iter(v.values())) for k, v in r.get("fields", {}).items()}
    d["cambiado"] = float(d.get("cambiado", 0))
    return d


def novedades() -> dict | None:
    """El documento público de novedades (mensaje, version, descarga), o None si no hay."""
    url = (f"https://firestore.googleapis.com/v1/projects/{_config()['projectId']}"
           f"/databases/(default)/documents/publico/novedades")
    estado, r = _pedir("GET", url)
    if estado != 200:
        return None
    return {k: next(iter(v.values())) for k, v in r.get("fields", {}).items()}


def bajar_archivo(url: str, destino) -> None:
    """Baja un archivo grande (el instalador) sin cargarlo entero en memoria."""
    import shutil
    with urllib.request.urlopen(url, timeout=60) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def mensaje(error) -> str:
    return str(error) if isinstance(error, NubeError) else "Algo salió mal con la nube"
