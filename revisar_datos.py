import os
import sqlite3

# Ruta de la base de datos de Quipu (AppData\Roaming\Quipu\quipu.db)
ruta = os.path.join(os.environ["APPDATA"], "Quipu", "quipu.db")
print("Base de datos:", ruta)
print("Existe:", os.path.exists(ruta))
print()

conexion = sqlite3.connect(ruta)
cursor = conexion.cursor()

# Lista todas las tablas que hay en la base
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tablas = [fila[0] for fila in cursor.fetchall()]

for tabla in tablas:
    # Cuántos registros tiene cada tabla
    cursor.execute(f'SELECT COUNT(*) FROM "{tabla}"')
    cantidad = cursor.fetchone()[0]
    print(f"=== {tabla} ({cantidad} registros) ===")

    # Las columnas de la tabla: nombre y tipo
    cursor.execute(f'PRAGMA table_info("{tabla}")')
    for columna in cursor.fetchall():
        nombre, tipo = columna[1], columna[2]
        es_clave = "  <- clave" if columna[5] else ""
        print(f"   {nombre}: {tipo}{es_clave}")
    print()

print("=== Revisión de datos guardados ===")
conexion = sqlite3.connect(ruta)
cursor = conexion.cursor()

# Versión del formato de la base (0 = nunca se marcó)
cursor.execute("PRAGMA user_version")
print("Versión del formato:", cursor.fetchone()[0])
print()

# Muestra el último registro de cada tabla con todas sus columnas
for tabla in ["carpetas", "notas", "eventos", "respuestas"]:
    cursor.execute(f'SELECT * FROM "{tabla}" ORDER BY rowid DESC LIMIT 1')
    fila = cursor.fetchone()
    print(f"--- {tabla} ---")
    if fila is None:
        print("   (vacía)")
    else:
        columnas = [d[0] for d in cursor.description]
        for nombre, valor in zip(columnas, fila):
            # Corta los textos largos (como el html de la nota) para que se lea mejor
            texto = str(valor)
            if len(texto) > 60:
                texto = texto[:60] + "..."
            print(f"   {nombre}: {texto}")
    print()

conexion.close()