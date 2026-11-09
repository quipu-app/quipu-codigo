"""Prepara las tablas de Quipu para sincronizar con la versión del celu (y más adelante, con Drive).

Cada fila tiene:
- uid:      un id único que no choca entre la compu y el celu
- creada:   cuándo se creó
- cambiado: cuándo cambió por última vez (lo usa la sincronización, no la pantalla)
- borrada:  borrado suave; la fila queda como marca para avisarle al otro dispositivo
"""
import time
import uuid

VERSION_DATOS = 1                                             # subirla si cambia la forma de los datos
AHORA_SQL = "((julianday('now') - 2440587.5) * 86400.0)"      # la hora actual, igual que time.time()

# Las columnas que, si cambian, cuentan como un cambio para sincronizar
COLUMNAS_DATOS = {
    "carpetas": ["nombre", "color", "borrada"],
    "notas": ["carpeta_id", "titulo", "html", "texto", "fijada", "borrada"],
    "eventos": ["titulo", "fecha", "hora", "color", "aviso_min", "repetir", "borrada"],
}


def preparar(db, tabla: str):
    """Agrega lo que falte a la tabla, completa las filas viejas y deja los disparadores andando."""
    existentes = {fila[1] for fila in db.execute(f"PRAGMA table_info({tabla})")}
    for columna, tipo in [("uid", "TEXT"), ("creada", "REAL"), ("cambiado", "REAL"),
                          ("borrada", "INTEGER DEFAULT 0")]:
        if columna not in existentes:
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")

    # Las filas que ya existían reciben su id único y sus fechas
    ahora = time.time()
    for fila in db.execute(f"SELECT rowid FROM {tabla} WHERE uid IS NULL").fetchall():
        db.execute(f"UPDATE {tabla} SET uid = ? WHERE rowid = ?", (uuid.uuid4().hex, fila[0]))
    db.execute(f"UPDATE {tabla} SET creada = ? WHERE creada IS NULL", (ahora,))
    base = "COALESCE(modificada, creada)" if "modificada" in existentes else "creada"
    db.execute(f"UPDATE {tabla} SET cambiado = {base} WHERE cambiado IS NULL")

    # Al crear una fila: id único y fechas, solos
    db.execute(f"""CREATE TRIGGER IF NOT EXISTS sincro_{tabla}_alta AFTER INSERT ON {tabla}
        BEGIN
            UPDATE {tabla} SET uid = COALESCE(NEW.uid, lower(hex(randomblob(16)))),
                               creada = COALESCE(NEW.creada, {AHORA_SQL}),
                               cambiado = {AHORA_SQL}
            WHERE rowid = NEW.rowid;
        END""")
    # Al cambiar algo que importa: se actualiza "cambiado", solo
    columnas = ", ".join(COLUMNAS_DATOS[tabla])
    db.execute(f"""CREATE TRIGGER IF NOT EXISTS sincro_{tabla}_cambio AFTER UPDATE OF {columnas} ON {tabla}
        BEGIN
            UPDATE {tabla} SET cambiado = {AHORA_SQL} WHERE rowid = NEW.rowid;
        END""")
    db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS sincro_{tabla}_uid ON {tabla}(uid)")
    db.execute(f"PRAGMA user_version = {VERSION_DATOS}")
    db.commit()
