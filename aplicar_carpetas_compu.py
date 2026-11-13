"""Notas de la compu: cambiar nombre y color de una carpeta, y borrarla (sus notas quedan sueltas).
Se puede correr más de una vez sin duplicar nada."""
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
    Path("respaldos").mkdir(exist_ok=True)                      # fuera de quipu/, así no viaja en el programa
    (Path("respaldos") / (ruta.name + ".antes")).write_text(original, encoding="utf-8")
    ruta.write_text(texto, encoding="utf-8")
    print(f"  {ruta}: actualizado (copia en respaldos)")


# 1. almacen.py: guardar el cambio de nombre/color y el borrado
editar("quipu/almacen.py", [(
    "                              (nombre, color, orden))\n        self.db.commit()\n        return cur.lastrowid\n",
    "                              (nombre, color, orden))\n        self.db.commit()\n        return cur.lastrowid\n\n"
    "    def editar_carpeta(self, carpeta_id: int, nombre: str, color: str):\n"
    "        self.db.execute(\"UPDATE carpetas SET nombre = ?, color = ? WHERE id = ?\", (nombre, color, carpeta_id))\n"
    "        self.db.commit()\n\n"
    "    def borrar_carpeta(self, carpeta_id: int):\n"
    "        \"\"\"Borrado suave (así viaja por Drive). Sus notas no se borran: quedan sueltas.\"\"\"\n"
    "        self.db.execute(\"UPDATE notas SET carpeta_id = NULL WHERE carpeta_id = ?\", (carpeta_id,))\n"
    "        self.db.execute(\"UPDATE carpetas SET borrada = 1 WHERE id = ?\", (carpeta_id,))\n"
    "        self.db.commit()\n",
)], marca="def borrar_carpeta")

# 2. modulos/notas.py: lo que la página le puede pedir a Python
editar("quipu/modulos/notas.py", [(
    "        self.modulo.proceso.emit(\"Creando carpeta\", \"Creada\")\n        return carpeta_id\n",
    "        self.modulo.proceso.emit(\"Creando carpeta\", \"Creada\")\n        return carpeta_id\n\n"
    "    @Slot(int, str, str, result=bool)\n"
    "    def editar_carpeta(self, carpeta_id: int, nombre: str, color: str) -> bool:\n"
    "        nombre = nombre.strip()\n"
    "        if not nombre:\n"
    "            return False\n"
    "        self.almacen.editar_carpeta(carpeta_id, nombre, color)\n"
    "        self.modulo.proceso.emit(\"Guardando carpeta\", \"Guardada\")\n"
    "        return True\n\n"
    "    @Slot(int)\n"
    "    def borrar_carpeta(self, carpeta_id: int):\n"
    "        self.almacen.borrar_carpeta(carpeta_id)\n"
    "        self.modulo.proceso.emit(\"Borrando carpeta\", \"Borrada\")\n",
)], marca="def borrar_carpeta")

# 3. notas.html: los botones al lado del nombre de la carpeta abierta
editar("quipu/web/notas/notas.html", [(
    '      <span id="nombre-abierta"></span>\n',
    '      <span id="nombre-abierta"></span>\n'
    '      <button class="tecla" id="btn-editar-carpeta" title="Cambiar nombre y color">Editar</button>\n'
    '      <button class="tecla" id="btn-borrar-carpeta" title="Borrar la carpeta (sus notas quedan sueltas)">Borrar</button>\n',
)], marca="btn-editar-carpeta")

# 4. notas.css: los botones van a la derecha
editar("quipu/web/notas/notas.css", [(
    ".migas[hidden] { display: none; }\n",
    ".migas[hidden] { display: none; }\n"
    "#btn-editar-carpeta { margin-left: auto; }\n"
    "#btn-editar-carpeta, #btn-borrar-carpeta { width: auto; padding: 3px 10px; font-size: 13px; }\n",
)], marca="btn-editar-carpeta")

# 5. notas.js: el mismo panel de "nueva carpeta" sirve para editar, y el borrado con doble toque
editar("quipu/web/notas/notas.js", [
    ("let colorCarpeta = COLORES_CARPETA[0];\n",
     "let colorCarpeta = COLORES_CARPETA[0];\n"
     "let editandoCarpeta = null;   // id de la carpeta que se está editando, o null si se crea una nueva\n"
     "let confirmarBorrarCarpeta = 0;\n"),
    ("function abrirPanelCarpeta() {\n  $(\"panel-carpeta\").hidden = false;\n",
     "function abrirPanelCarpeta() {\n  editandoCarpeta = null;\n  $(\"btn-crear-carpeta\").textContent = \"Crear\";\n"
     "  $(\"panel-carpeta\").hidden = false;\n"),
    ("function crearCarpeta() {\n  const nombre = $(\"nombre-carpeta\").value.trim();\n  if (!nombre) { $(\"nombre-carpeta\").focus(); return; }\n",
     "function crearCarpeta() {\n  const nombre = $(\"nombre-carpeta\").value.trim();\n  if (!nombre) { $(\"nombre-carpeta\").focus(); return; }\n"
     "  if (editandoCarpeta !== null) {\n"
     "    puente.editar_carpeta(editandoCarpeta, nombre, colorCarpeta, () => {\n"
     "      $(\"panel-carpeta\").hidden = true;\n"
     "      editandoCarpeta = null;\n"
     "      cargarInicio();\n"
     "    });\n"
     "    return;\n"
     "  }\n"),
    ("// --- Reordenar arrastrando",
     "// --- Editar y borrar la carpeta abierta ---------------------------------------------\n"
     "function abrirEditarCarpeta() {\n"
     "  const c = carpetas.find((x) => x.id === carpetaAbierta);\n"
     "  if (!c) return;\n"
     "  editandoCarpeta = c.id;\n"
     "  $(\"btn-crear-carpeta\").textContent = \"Guardar\";\n"
     "  $(\"panel-carpeta\").hidden = false;\n"
     "  $(\"nombre-carpeta\").value = c.nombre;\n"
     "  colorCarpeta = c.color;\n"
     "  dibujarColoresCarpeta();\n"
     "  $(\"nombre-carpeta\").focus();\n"
     "}\n\n"
     "function borrarCarpeta() {\n"
     "  const boton = $(\"btn-borrar-carpeta\");\n"
     "  if (Date.now() > confirmarBorrarCarpeta) {          // primer toque: pide confirmar\n"
     "    confirmarBorrarCarpeta = Date.now() + 3000;\n"
     "    boton.textContent = \"¿Seguro? Tocá de nuevo\";\n"
     "    setTimeout(() => { boton.textContent = \"Borrar\"; }, 3000);\n"
     "    return;\n"
     "  }\n"
     "  confirmarBorrarCarpeta = 0;\n"
     "  boton.textContent = \"Borrar\";\n"
     "  puente.borrar_carpeta(carpetaAbierta, () => {\n"
     "    $(\"panel-carpeta\").hidden = true;\n"
     "    cambiarVista(\"carpetas\");\n"
     "  });\n"
     "}\n\n"
     "// --- Reordenar arrastrando"),
    ("$(\"btn-crear-carpeta\").onclick = crearCarpeta;\n",
     "$(\"btn-crear-carpeta\").onclick = crearCarpeta;\n"
     "$(\"btn-editar-carpeta\").onclick = abrirEditarCarpeta;\n"
     "$(\"btn-borrar-carpeta\").onclick = borrarCarpeta;\n"),
], marca="function abrirEditarCarpeta")

print("\nListo.")