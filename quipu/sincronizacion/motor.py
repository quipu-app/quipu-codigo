import json
import sqlite3
import time
import uuid

import config
from . import google_drive

RUTA_DB = config.CARPETA_DATOS / "quipu.db"
NOMBRE_ARCHIVO = "quipu_datos.json"
FORMATO = 1

TABLAS_CON_UID = ["carpetas", "notas", "eventos"]
TODAS_LAS_TABLAS = TABLAS_CON_UID + ["respuestas"]


# ---------- Utilidades de la base ----------

def _conectar():
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    return con


def _columnas(con, tabla):
    return [fila[1] for fila in con.execute(f'PRAGMA table_info("{tabla}")')]


def _completar_faltantes(con):
    """Por las dudas: a todo registro viejo sin uid o sin fecha de cambio se le pone uno."""
    for tabla in TABLAS_CON_UID:
        filas = con.execute(
            f"SELECT id, uid, creada, cambiado FROM {tabla} "
            f"WHERE uid IS NULL OR uid = '' OR cambiado IS NULL"
        ).fetchall()
        for fila in filas:
            uid = fila["uid"] or uuid.uuid4().hex
            cambiado = fila["cambiado"] or fila["creada"] or time.time()
            con.execute(f"UPDATE {tabla} SET uid = ?, cambiado = ? WHERE id = ?", (uid, cambiado, fila["id"]))
    con.commit()


# ---------- De la base local a un diccionario ----------

def exportar(con):
    """Lee la base y devuelve {tabla: {clave: registro}}, usando uid en lugar de los id locales."""
    mapa_carpetas = {f["id"]: f["uid"] for f in con.execute("SELECT id, uid FROM carpetas")}
    mapa_eventos = {f["id"]: f["uid"] for f in con.execute("SELECT id, uid FROM eventos")}

    datos = {}
    for tabla in TABLAS_CON_UID:
        registros = {}
        for fila in con.execute(f"SELECT * FROM {tabla}"):
            registro = dict(fila)
            registro.pop("id", None)
            if tabla == "notas":
                registro["carpeta_uid"] = mapa_carpetas.get(registro.pop("carpeta_id", None))
            registros[registro["uid"]] = registro
        datos[tabla] = registros

    respuestas = {}
    for fila in con.execute("SELECT * FROM respuestas"):
        registro = dict(fila)
        evento_uid = mapa_eventos.get(registro.pop("evento_id", None))
        if not evento_uid:
            continue
        registro["evento_uid"] = evento_uid
        respuestas[f"{evento_uid}|{registro['dia']}"] = registro
    datos["respuestas"] = respuestas
    return datos


# ---------- Unir local con Drive ----------

def _marca(tabla, registro):
    """Fecha que decide quién gana: cambiado (o creada, en respuestas)."""
    if tabla == "respuestas":
        return registro.get("creada") or 0
    return registro.get("cambiado") or 0


def unir(local, remoto):
    """Devuelve (lo unido, lo que hay que guardar en la compu, si hay que subir a Drive)."""
    unido = {}
    para_aplicar = {}
    hay_que_subir = False

    for tabla in TODAS_LAS_TABLAS:
        de_aca = local.get(tabla, {})
        de_drive = remoto.get(tabla, {})
        unido[tabla] = {}
        para_aplicar[tabla] = []

        for clave in set(de_aca) | set(de_drive):
            mio = de_aca.get(clave)
            suyo = de_drive.get(clave)

            if suyo is None:                       # solo está acá: hay que subirlo
                ganador = mio
                hay_que_subir = True
            elif mio is None:                      # solo está en Drive: hay que bajarlo
                ganador = suyo
                para_aplicar[tabla].append(suyo)
            elif _marca(tabla, suyo) > _marca(tabla, mio):   # el de Drive es más nuevo
                ganador = suyo
                para_aplicar[tabla].append(suyo)
            else:                                  # el de acá es igual o más nuevo
                ganador = mio
                if _marca(tabla, mio) > _marca(tabla, suyo):
                    hay_que_subir = True

            unido[tabla][clave] = ganador

    return unido, para_aplicar, hay_que_subir


# ---------- Del diccionario a la base local ----------

def _guardar_registro(con, tabla, registro, columnas):
    """Actualiza el registro si su uid ya existe; si no, lo crea."""
    valores = {k: v for k, v in registro.items() if k in columnas and k != "id"}
    existe = con.execute(f"SELECT id FROM {tabla} WHERE uid = ?", (registro["uid"],)).fetchone()
    if existe:
        asignaciones = ", ".join(f'"{k}" = ?' for k in valores)
        con.execute(f"UPDATE {tabla} SET {asignaciones} WHERE id = ?", [*valores.values(), existe["id"]])
    else:
        nombres = ", ".join(f'"{k}"' for k in valores)
        signos = ", ".join("?" for _ in valores)
        con.execute(f"INSERT INTO {tabla} ({nombres}) VALUES ({signos})", list(valores.values()))

    # Los disparadores de sincro.py le ponen "ahora" a cambiado al guardar.
    # Le devolvemos la fecha original, para que no parezca un cambio nuevo hecho en este aparato.
    # (Cambiar solo "cambiado" no despierta a esos disparadores.)
    con.execute(f"UPDATE {tabla} SET cambiado = ? WHERE uid = ?", (registro.get("cambiado"), registro["uid"]))


def aplicar(con, para_aplicar):
    """Guarda en quipu.db lo que llegó de Drive, traduciendo uid a id locales."""
    # Carpetas primero, porque las notas apuntan a ellas
    columnas = _columnas(con, "carpetas")
    for registro in para_aplicar["carpetas"]:
        _guardar_registro(con, "carpetas", registro, columnas)

    mapa_carpetas = {f["uid"]: f["id"] for f in con.execute("SELECT id, uid FROM carpetas")}
    columnas = _columnas(con, "notas")
    for registro in para_aplicar["notas"]:
        registro = dict(registro)
        registro["carpeta_id"] = mapa_carpetas.get(registro.pop("carpeta_uid", None))
        _guardar_registro(con, "notas", registro, columnas)

    columnas = _columnas(con, "eventos")
    for registro in para_aplicar["eventos"]:
        _guardar_registro(con, "eventos", registro, columnas)

    # Respuestas al final, porque apuntan a los eventos
    mapa_eventos = {f["uid"]: f["id"] for f in con.execute("SELECT id, uid FROM eventos")}
    columnas = _columnas(con, "respuestas")
    for registro in para_aplicar["respuestas"]:
        registro = dict(registro)
        registro["evento_id"] = mapa_eventos.get(registro.pop("evento_uid", None))
        if registro["evento_id"] is None:
            continue
        valores = {k: v for k, v in registro.items() if k in columnas}
        nombres = ", ".join(f'"{k}"' for k in valores)
        signos = ", ".join("?" for _ in valores)
        con.execute(f"INSERT OR REPLACE INTO respuestas ({nombres}) VALUES ({signos})", list(valores.values()))

    con.commit()


# ---------- Para notar cambios sin sincronizar ----------

def marca_local():
    """Una "foto" rápida de los datos: la última fecha de cambio y cuántos registros hay."""
    con = sqlite3.connect(RUTA_DB)
    try:
        fechas = [con.execute(f"SELECT MAX(cambiado) FROM {t}").fetchone()[0] or 0 for t in TABLAS_CON_UID]
        fechas.append(con.execute("SELECT MAX(creada) FROM respuestas").fetchone()[0] or 0)
        cantidad = sum(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TODAS_LAS_TABLAS)
        return max(fechas), cantidad
    except sqlite3.Error:
        return None
    finally:
        con.close()


# ---------- Formato del archivo en Drive ----------

def _a_archivo(unido, perfil):
    return {
        "formato": FORMATO,
        "perfil": perfil,
        "actualizado": time.time(),
        "tablas": {tabla: list(registros.values()) for tabla, registros in unido.items()},
    }


def _desde_archivo(archivo):
    remoto = {}
    for tabla, lista in archivo.get("tablas", {}).items():
        if tabla == "respuestas":
            remoto[tabla] = {f"{r['evento_uid']}|{r['dia']}": r for r in lista}
        else:
            remoto[tabla] = {r["uid"]: r for r in lista}
    return remoto


# ---------- Todo junto ----------

def sincronizar(permitir_navegador=False, perfil=None):
    """Sincroniza quipu.db con Drive. Devuelve un resumen de lo que hizo."""
    llave = google_drive.obtener_llave(permitir_navegador)
    if llave is None:
        return {"estado": "sin_conectar"}

    drive = google_drive.servicio(llave)
    archivo, id_archivo = google_drive.bajar_json(drive, NOMBRE_ARCHIVO)

    if archivo and archivo.get("formato", 1) > FORMATO:
        # Lo subió una versión más nueva de Quipu: no lo pisamos
        return {"estado": "formato_nuevo"}

    remoto = _desde_archivo(archivo) if archivo else {}

    # El nombre de usuario: gana el que se cambió más recientemente
    perfil = perfil or {}
    perfil_drive = (archivo or {}).get("perfil") or {}
    perfil_final, perfil_bajado, subir_perfil = perfil, None, False
    if (perfil_drive.get("nombre_cambiado") or 0) > (perfil.get("nombre_cambiado") or 0):
        perfil_final = perfil_bajado = perfil_drive
    elif (perfil.get("nombre_cambiado") or 0) > (perfil_drive.get("nombre_cambiado") or 0):
        subir_perfil = True

    con = _conectar()
    try:
        _completar_faltantes(con)
        local = exportar(con)
        unido, para_aplicar, hay_que_subir = unir(local, remoto)
        aplicar(con, para_aplicar)
        hay_que_subir = hay_que_subir or subir_perfil

        tamano_kb = 0
        if hay_que_subir or archivo is None:
            contenido = _a_archivo(unido, perfil_final)
            tamano_kb = round(len(json.dumps(contenido, ensure_ascii=False).encode("utf-8")) / 1024, 1)
            google_drive.subir_json(drive, NOMBRE_ARCHIVO, contenido, id_archivo)
    finally:
        con.close()

    return {
        "estado": "listo",
        "bajados": {tabla: len(lista) for tabla, lista in para_aplicar.items()},
        "subido": hay_que_subir or archivo is None,
        "tamano_kb": tamano_kb,
        "perfil": perfil_bajado,
    }
