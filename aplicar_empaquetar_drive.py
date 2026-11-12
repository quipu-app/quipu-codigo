"""Prepara empaquetar.py para la sincronización con Drive. Se puede correr más de una vez."""
from pathlib import Path

ruta = Path("empaquetar.py")
texto = ruta.read_text(encoding="utf-8-sig")
if "credenciales_google.json" in texto:
    print("  empaquetar.py: ya estaba, no lo toqué")
    raise SystemExit

original = texto
reemplazos = [
    # Frenar si faltan las credenciales, igual que con firebase.json
    ('    raise SystemExit("Falta quipu/firebase.json: sin él, Colaborar no anda en el programa.")\n',
     '    raise SystemExit("Falta quipu/firebase.json: sin él, Colaborar no anda en el programa.")\n'
     'if not (raiz / "sincronizacion" / "credenciales_google.json").exists():\n'
     '    raise SystemExit("Falta quipu/sincronizacion/credenciales_google.json: sin él, no se puede conectar Google Drive.")\n'),
    # Avisar también por los respaldos .antes2
    ('sobrantes = list(raiz.rglob("*.antes"))\n',
     'sobrantes = list(raiz.rglob("*.antes")) + list(raiz.rglob("*.antes2"))\n'),
    # Copiar las credenciales al lado de google_drive.py, y los datos de la librería de Drive
    ('    "--add-data", f"{raiz / \'firebase.json\'}{sep}.", # la conexión con Firebase\n',
     '    "--add-data", f"{raiz / \'firebase.json\'}{sep}.", # la conexión con Firebase\n'
     '    "--add-data", f"{raiz / \'sincronizacion\' / \'credenciales_google.json\'}{sep}sincronizacion",  # Google Drive\n'
     '    "--collect-data", "googleapiclient",             # las descripciones de las APIs de Google\n'
     '    "--hidden-import", "sincronizacion.google_drive",\n'
     '    "--hidden-import", "sincronizacion.motor",\n'),
]
for viejo, nuevo in reemplazos:
    if viejo not in texto:
        raise SystemExit(f"  ERROR: no encontré en empaquetar.py:\n{viejo}")
    texto = texto.replace(viejo, nuevo, 1)

Path("empaquetar.py.antes").write_text(original, encoding="utf-8")
ruta.write_text(texto, encoding="utf-8")
print("  empaquetar.py: actualizado (copia en empaquetar.py.antes)")