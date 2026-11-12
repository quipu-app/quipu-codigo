"""Suma lo de Google Drive a Quipu.spec y a la compilación de GitHub. Se puede correr más de una vez."""
from pathlib import Path


def editar(ruta, reemplazos, marca):
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8-sig")
    if marca in texto:
        print(f"  {ruta}: ya estaba, no lo toqué")
        return
    original = texto
    for viejo, nuevo in reemplazos:
        if viejo not in texto:
            raise SystemExit(f"  ERROR en {ruta}: no encontré\n{viejo}")
        texto = texto.replace(viejo, nuevo, 1)
    ruta.with_name(ruta.name + ".antes").write_text(original, encoding="utf-8")
    ruta.write_text(texto, encoding="utf-8")
    print(f"  {ruta}: actualizado")


# 1. Quipu.spec: las credenciales, los datos de la librería de Drive y los módulos de sincronización
editar("Quipu.spec", [
    ("# -*- mode: python ; coding: utf-8 -*-\n",
     "# -*- mode: python ; coding: utf-8 -*-\n"
     "from PyInstaller.utils.hooks import collect_data_files\n"),
    ("datas=[('quipu/assets', 'assets'), ('quipu/web', 'web'), ('quipu/firebase.json', '.')],",
     "datas=[('quipu/assets', 'assets'), ('quipu/web', 'web'), ('quipu/firebase.json', '.'),\n"
     "           ('quipu/sincronizacion/credenciales_google.json', 'sincronizacion')]\n"
     "          + collect_data_files('googleapiclient'),"),
    ("'modulos.tiempo', 'modulos.web']",
     "'modulos.tiempo', 'modulos.web',\n"
     "                   'sincronizacion', 'sincronizacion.google_drive', 'sincronizacion.motor']"),
], marca="credenciales_google.json")

# 2. compilar.yml: escribir las credenciales desde el secreto antes de armar
editar(".github/workflows/compilar.yml", [
    ("      - name: Armar Quipu con PyInstaller\n",
     "      - name: Poner las credenciales de Google (desde el secreto del repositorio)\n"
     "        shell: pwsh\n"
     "        env:\n"
     "          CREDENCIALES: ${{ secrets.GOOGLE_CREDENCIALES }}\n"
     "        run: |\n"
     "          if (-not $env:CREDENCIALES) { throw \"Falta el secreto GOOGLE_CREDENCIALES\" }\n"
     "          [IO.File]::WriteAllText(\"quipu/sincronizacion/credenciales_google.json\", $env:CREDENCIALES)\n"
     "\n"
     "      - name: Armar Quipu con PyInstaller\n"),
], marca="GOOGLE_CREDENCIALES")