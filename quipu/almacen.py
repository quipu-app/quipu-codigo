import sqlite3
import time

import config
import sincro


class Almacen:
    """Guarda notas y carpetas en un archivo SQLite dentro de la carpeta de datos de Quipu."""

    def __init__(self):
        config.CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(config.CARPETA_DATOS / "quipu.db")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS carpetas (
                id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, color TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY, carpeta_id INTEGER, html TEXT NOT NULL, texto TEXT NOT NULL,
                fijada INTEGER DEFAULT 0, borrada INTEGER DEFAULT 0, creada REAL, modificada REAL
            );
        """)
        # Columnas nuevas: se agregan solas si la base es de una versión anterior
        self._asegurar_columna("notas", "titulo", "TEXT DEFAULT ''")
        self._asegurar_columna("notas", "orden", "REAL DEFAULT 0")
        self._asegurar_columna("carpetas", "orden", "REAL DEFAULT 0")
        self._asegurar_columna("notas", "codigo", "TEXT DEFAULT ''")   # código si está compartida
        self._asegurar_columna("notas", "remoto", "REAL DEFAULT 0")     # última versión vista en la nube
        # Preparadas para sincronizar con el celu: id único, fechas y borrado suave
        sincro.preparar(self.db, "carpetas")
        sincro.preparar(self.db, "notas")
        # Las notas borradas quedan como marca vacía, para avisarle al celu que se borraron
        self.db.execute("UPDATE notas SET titulo = '', html = '', texto = '' "
                        "WHERE borrada = 1 AND (html != '' OR texto != '')")
        self.db.commit()

    def _asegurar_columna(self, tabla: str, columna: str, tipo: str):
        existentes = [fila["name"] for fila in self.db.execute(f"PRAGMA table_info({tabla})")]
        if columna not in existentes:
            self.db.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")

    # --- Carpetas --------------------------------------------------------------------
    def carpetas(self):
        return self.db.execute("SELECT * FROM carpetas WHERE borrada = 0 ORDER BY orden, nombre").fetchall()

    def carpeta(self, carpeta_id):
        return self.db.execute("SELECT * FROM carpetas WHERE id = ?", (carpeta_id,)).fetchone()

    def crear_carpeta(self, nombre: str, color: str) -> int:
        orden = self.db.execute("SELECT COALESCE(MAX(orden), 0) + 1 FROM carpetas").fetchone()[0]
        cur = self.db.execute("INSERT INTO carpetas (nombre, color, orden) VALUES (?, ?, ?)",
                              (nombre, color, orden))
        self.db.commit()
        return cur.lastrowid

    def contar_notas(self, carpeta_id) -> int:
        return self.db.execute("SELECT COUNT(*) FROM notas WHERE borrada = 0 AND carpeta_id = ?",
                               (carpeta_id,)).fetchone()[0]

    def color_carpeta(self, carpeta_id) -> str | None:
        fila = self.carpeta(carpeta_id)
        return fila["color"] if fila else None

    def ordenar_carpetas(self, ids: list[int]):
        for i, carpeta_id in enumerate(ids):
            self.db.execute("UPDATE carpetas SET orden = ? WHERE id = ?", (i, carpeta_id))
        self.db.commit()

    # --- Notas -------------------------------------------------------------------------
    def notas(self, carpeta_id=None, buscar: str = ""):
        sql, params = "SELECT * FROM notas WHERE borrada = 0", []
        if carpeta_id is not None:
            sql += " AND carpeta_id = ?"
            params.append(carpeta_id)
        if buscar:
            sql += " AND (texto LIKE ? OR titulo LIKE ?)"
            params += [f"%{buscar}%", f"%{buscar}%"]
        sql += " ORDER BY fijada DESC, orden, modificada DESC"
        return self.db.execute(sql, params).fetchall()

    def nota(self, nota_id: int):
        return self.db.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()

    def guardar_nota(self, nota_id, titulo: str, html: str, texto: str, carpeta_id) -> int:
        ahora = time.time()
        if nota_id is None:
            orden = self.db.execute("SELECT COALESCE(MIN(orden), 0) - 1 FROM notas").fetchone()[0]
            cur = self.db.execute(
                "INSERT INTO notas (carpeta_id, titulo, html, texto, creada, modificada, orden) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (carpeta_id, titulo, html, texto, ahora, ahora, orden))
            nota_id = cur.lastrowid
        else:
            self.db.execute(
                "UPDATE notas SET carpeta_id = ?, titulo = ?, html = ?, texto = ?, modificada = ? WHERE id = ?",
                (carpeta_id, titulo, html, texto, ahora, nota_id))
        self.db.commit()
        return nota_id

    def ordenar_notas(self, ids: list[int]):
        for i, nota_id in enumerate(ids):
            self.db.execute("UPDATE notas SET orden = ? WHERE id = ?", (i, nota_id))
        self.db.commit()

    def fijar(self, nota_id: int, fijada: bool):
        self.db.execute("UPDATE notas SET fijada = ? WHERE id = ?", (int(fijada), nota_id))
        self.db.commit()

    def borrar(self, nota_id: int, borrada: bool = True):
        self.db.execute("UPDATE notas SET borrada = ? WHERE id = ?", (int(borrada), nota_id))
        self.db.commit()

    # --- Notas compartidas ------------------------------------------------------------
    def marcar_compartida(self, nota_id: int, codigo: str, remoto: float):
        self.db.execute("UPDATE notas SET codigo = ?, remoto = ? WHERE id = ?", (codigo, remoto, nota_id))
        self.db.commit()

    def nota_por_codigo(self, codigo: str):
        return self.db.execute("SELECT * FROM notas WHERE codigo = ? AND borrada = 0",
                               (codigo,)).fetchone()

    def actualizar_desde_nube(self, nota_id: int, titulo: str, html: str, texto: str, remoto: float):
        self.db.execute("UPDATE notas SET titulo = ?, html = ?, texto = ?, modificada = ?, remoto = ? "
                        "WHERE id = ?", (titulo, html, texto, time.time(), remoto, nota_id))
        self.db.commit()