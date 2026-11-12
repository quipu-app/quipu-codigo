import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "quipu"))
from sincronizacion import google_drive


def hora(segundos):
    return datetime.fromtimestamp(segundos).strftime("%d/%m %H:%M:%S") if segundos else "-"


llave = google_drive.obtener_llave()
if llave is None:
    sys.exit("No estás conectado a Google: conectate desde Ajustes → Datos.")

drive = google_drive.servicio(llave)
archivo, _ = google_drive.bajar_json(drive, "quipu_datos.json")
if not archivo:
    sys.exit("Todavía no hay datos de Quipu en Drive.")

tablas = archivo.get("tablas", {})
perfil = archivo.get("perfil") or {}

print("=== Lo que hay en Drive ===")
print("Última subida:", hora(archivo.get("actualizado")))
print("Nombre:", perfil.get("nombre") or "(sin nombre)", "| cambiado:", hora(perfil.get("nombre_cambiado")))
print()

for tabla in ["carpetas", "notas", "eventos", "respuestas"]:
    lista = tablas.get(tabla, [])
    borradas = sum(1 for r in lista if r.get("borrada"))
    print(f"{tabla}: {len(lista) - borradas} ({borradas} borradas)")

print("\n--- Últimas notas que cambiaron ---")
notas = sorted(tablas.get("notas", []), key=lambda r: r.get("cambiado") or 0, reverse=True)
for n in notas[:5]:
    titulo = n.get("titulo") or (n.get("texto") or "")[:30] or "(sin título)"
    marca = "  [borrada]" if n.get("borrada") else ""
    print(f"   {hora(n.get('cambiado'))}  {titulo}{marca}")

print("\n--- Últimos eventos que cambiaron ---")
eventos = sorted(tablas.get("eventos", []), key=lambda r: r.get("cambiado") or 0, reverse=True)
for e in eventos[:5]:
    marca = "  [borrado]" if e.get("borrada") else ""
    print(f"   {hora(e.get('cambiado'))}  {e.get('titulo')} ({e.get('fecha')} {e.get('hora') or ''}){marca}")
