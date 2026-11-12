import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

PERMISOS = ["https://www.googleapis.com/auth/drive.appdata"]

CARPETA_QUIPU = os.path.join(os.environ["APPDATA"], "Quipu")
RUTA_TOKEN = os.path.join(CARPETA_QUIPU, "token_google.json")
RUTA_CREDENCIALES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credenciales_google.json")


def esta_conectado():
    return os.path.exists(RUTA_TOKEN)


def desconectar():
    if os.path.exists(RUTA_TOKEN):
        os.remove(RUTA_TOKEN)


def _guardar_llave(llave):
    os.makedirs(CARPETA_QUIPU, exist_ok=True)
    with open(RUTA_TOKEN, "w", encoding="utf-8") as archivo:
        archivo.write(llave.to_json())


def obtener_llave(permitir_navegador=False):
    """Devuelve la llave de Google, o None si no hay y no se permite abrir el navegador."""
    llave = None
    if os.path.exists(RUTA_TOKEN):
        try:
            llave = Credentials.from_authorized_user_file(RUTA_TOKEN, PERMISOS)
        except Exception:
            llave = None

    if llave and llave.valid:
        return llave

    if llave and llave.expired and llave.refresh_token:
        try:
            llave.refresh(Request())
            _guardar_llave(llave)
            return llave
        except Exception:
            llave = None

    if not permitir_navegador:
        return None

    flujo = InstalledAppFlow.from_client_secrets_file(RUTA_CREDENCIALES, PERMISOS)
    llave = flujo.run_local_server(
        port=0,
        timeout_seconds=180,
        success_message="Listo, ya podés cerrar esta pestaña y volver a Quipu.",
    )
    _guardar_llave(llave)
    return llave


def servicio(llave):
    return build("drive", "v3", credentials=llave, cache_discovery=False)


def _buscar(drive, nombre):
    respuesta = drive.files().list(
        spaces="appDataFolder",
        q=f"name = '{nombre}'",
        fields="files(id)",
    ).execute()
    archivos = respuesta.get("files", [])
    return archivos[0]["id"] if archivos else None


def bajar_json(drive, nombre):
    """Devuelve (contenido, id) del archivo, o (None, None) si todavía no existe."""
    id_archivo = _buscar(drive, nombre)
    if not id_archivo:
        return None, None
    contenido = drive.files().get_media(fileId=id_archivo).execute()
    return json.loads(contenido.decode("utf-8")), id_archivo


def subir_json(drive, nombre, datos, id_archivo=None):
    contenido = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    media = MediaInMemoryUpload(contenido, mimetype="application/json")
    if id_archivo:
        drive.files().update(fileId=id_archivo, media_body=media).execute()
    else:
        cuerpo = {"name": nombre, "parents": ["appDataFolder"]}
        drive.files().create(body=cuerpo, media_body=media, fields="id").execute()
