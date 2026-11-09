"""Los datos de la Agenda: guardar eventos y calcular cuándo ocurren (incluidos los que se repiten)."""
import calendar
import sqlite3
import time
from datetime import date, datetime, timedelta

import config
import sincro

REPETICIONES = {"no": "No se repite", "dia": "Todos los días", "semana": "Todas las semanas",
                "mes": "Todos los meses", "anio": "Todos los años"}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


class Agenda:
    def __init__(self):
        config.CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(config.CARPETA_DATOS / "quipu.db")
        self.db.row_factory = sqlite3.Row
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY,
                titulo TEXT NOT NULL,
                fecha TEXT NOT NULL,          -- AAAA-MM-DD: el primer día que ocurre
                hora TEXT DEFAULT '',         -- HH:MM, o vacío si es de todo el día
                color TEXT DEFAULT '#E5484D',
                aviso_min INTEGER DEFAULT 10, -- minutos antes para avisar (0 = sin aviso)
                repetir TEXT DEFAULT 'no'     -- no, dia, semana, mes, anio
            )""")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS respuestas (
                evento_id INTEGER, dia TEXT, respuesta TEXT, creada REAL,
                PRIMARY KEY (evento_id, dia)
            )""")
        sincro.preparar(self.db, "eventos")   # id único, fechas y borrado suave
        self.db.commit()

    # --- Guardar, cambiar y borrar -----------------------------------------------------------
    def guardar(self, evento_id, titulo, fecha, hora="", color="#E5484D", aviso_min=10, repetir="no") -> int:
        datos = (titulo.strip(), fecha, hora, color, int(aviso_min), repetir)
        if evento_id is None:
            cur = self.db.execute("INSERT INTO eventos (titulo, fecha, hora, color, aviso_min, repetir) "
                                  "VALUES (?, ?, ?, ?, ?, ?)", datos)
            evento_id = cur.lastrowid
        else:
            self.db.execute("UPDATE eventos SET titulo=?, fecha=?, hora=?, color=?, aviso_min=?, repetir=? "
                            "WHERE id=?", (*datos, evento_id))
        self.db.commit()
        return evento_id

    def borrar(self, evento_id: int):
        self.db.execute("UPDATE eventos SET borrada = 1 WHERE id = ?", (evento_id,))
        self.db.commit()

    def evento(self, evento_id: int):
        return self.db.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    # --- ¿Se hizo? (la pregunta de después) -------------------------------------------------
    def respondido(self, evento_id: int, dia: str) -> bool:
        return self.db.execute("SELECT 1 FROM respuestas WHERE evento_id = ? AND dia = ?",
                               (evento_id, dia)).fetchone() is not None

    def responder(self, evento_id: int, dia: str, respuesta: str):
        self.db.execute("INSERT OR REPLACE INTO respuestas (evento_id, dia, respuesta, creada) "
                        "VALUES (?, ?, ?, ?)", (evento_id, dia, respuesta, time.time()))
        self.db.commit()

    def para_preguntar(self, ahora: datetime, despues_min: int) -> dict | None:
        """El primer evento de hoy que pasó hace al menos despues_min minutos y no se respondió."""
        for o in self.del_dia(ahora.date()):
            if not o["hora"]:
                continue                                  # los de todo el día no se preguntan
            inicio = datetime.fromisoformat(f"{o['dia']}T{o['hora']}")
            if inicio + timedelta(minutes=despues_min) <= ahora and not self.respondido(o["id"], o["dia"]):
                return o
        return None

    # --- Cuándo ocurre cada evento -------------------------------------------------------------
    @staticmethod
    def _ocurre(ev, dia: date) -> bool:
        """¿Este evento ocurre en este día? Tiene en cuenta las repeticiones."""
        inicio = date.fromisoformat(ev["fecha"])
        if dia < inicio:
            return False
        r = ev["repetir"]
        if r == "no":
            return dia == inicio
        if r == "dia":
            return True
        if r == "semana":
            return dia.weekday() == inicio.weekday()
        if r == "mes":
            # Si el evento es un 31 y el mes no lo tiene, cae el último día del mes
            ultimo = calendar.monthrange(dia.year, dia.month)[1]
            return dia.day == min(inicio.day, ultimo)
        if r == "anio":
            return (dia.month, dia.day) == (inicio.month, inicio.day)
        return False

    def ocurrencias(self, desde: date, hasta: date) -> list[dict]:
        """Todas las veces que ocurre algo entre dos días (incluidos), ordenadas por día y hora."""
        eventos = self.db.execute("SELECT * FROM eventos WHERE fecha <= ? AND borrada = 0", (hasta.isoformat(),)).fetchall()
        resultado = []
        dia = desde
        while dia <= hasta:
            for ev in eventos:
                if self._ocurre(ev, dia):
                    resultado.append({**dict(ev), "dia": dia.isoformat()})
            dia += timedelta(days=1)
        resultado.sort(key=lambda o: (o["dia"], o["hora"] or "00:00"))
        return resultado

    def del_mes(self, anio: int, mes: int) -> list[dict]:
        ultimo = calendar.monthrange(anio, mes)[1]
        return self.ocurrencias(date(anio, mes, 1), date(anio, mes, ultimo))

    def del_dia(self, dia: date) -> list[dict]:
        return self.ocurrencias(dia, dia)

    # --- Lo que viene (para los avisos y la pantallita) ---------------------------------------
    def proximos(self, ahora: datetime, horas: int = 24) -> list[dict]:
        """Lo que empieza desde ahora hasta dentro de 'horas', con la hora de inicio y la del aviso."""
        resultado = []
        for o in self.ocurrencias(ahora.date(), (ahora + timedelta(hours=horas)).date()):
            if not o["hora"]:
                continue                                  # los de todo el día no tienen aviso por hora
            inicio = datetime.fromisoformat(f"{o['dia']}T{o['hora']}")
            if ahora <= inicio <= ahora + timedelta(hours=horas):
                o["inicio"] = inicio
                o["avisar_en"] = inicio - timedelta(minutes=o["aviso_min"]) if o["aviso_min"] else None
                resultado.append(o)
        return resultado


def nombre_dia(dia: date) -> str:
    """'Miércoles 21'."""
    return f"{DIAS[dia.weekday()]} {dia.day}"


# --- Prueba desde la terminal ---------------------------------------------------------------
if __name__ == "__main__":
    a = Agenda()
    hoy = date.today()
    print("Creo tres eventos de prueba...")
    ids = [
        a.guardar(None, "Dentista", (hoy + timedelta(days=3)).isoformat(), "15:00", "#E5484D", 10, "no"),
        a.guardar(None, "Clase de inglés", hoy.isoformat(), "19:00", "#3FA9F5", 30, "semana"),
        a.guardar(None, "Cumple de mamá", hoy.replace(day=1).isoformat(), "", "#F2994A", 0, "anio"),
    ]
    print(f"\n{MESES[hoy.month - 1]} {hoy.year}:")
    for o in a.del_mes(hoy.year, hoy.month):
        d = date.fromisoformat(o["dia"])
        print(f"  {nombre_dia(d):14} {o['hora'] or 'todo el día':12} {o['titulo']}  ({REPETICIONES[o['repetir']]})")
    print("\nPróximas 24 horas:")
    for o in a.proximos(datetime.now()):
        aviso = o["avisar_en"].strftime("%H:%M") if o["avisar_en"] else "sin aviso"
        print(f"  {o['inicio']:%d/%m %H:%M}  {o['titulo']}  (aviso a las {aviso})")
    print("\nBorro los eventos de prueba.")
    for i in ids:
        a.borrar(i)