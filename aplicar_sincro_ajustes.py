"""Suma la sincronización con Drive a Ajustes. Se puede correr más de una vez sin duplicar nada."""
from pathlib import Path


def editar(ruta, reemplazos, marca):
    """Aplica los reemplazos a un archivo, con copia .antes. 'marca' indica si ya estaba hecho."""
    ruta = Path(ruta)
    texto = ruta.read_text(encoding="utf-8-sig")
    if marca in texto:
        print(f"  {ruta}: ya estaba, no lo toqué")
        return
    original = texto
    for viejo, nuevo in reemplazos:
        if viejo not in texto:
            raise SystemExit(f"  ERROR en {ruta}: no encontré este pedazo:\n{viejo}\n(no se cambió ningún archivo de acá en adelante)")
        texto = texto.replace(viejo, nuevo, 1)
    ruta.with_name(ruta.name + ".antes").write_text(original, encoding="utf-8")
    ruta.write_text(texto, encoding="utf-8")
    print(f"  {ruta}: actualizado (copia en {ruta.name}.antes)")


# 1. ajustes.py: recordar cuándo fue la última sincronización (por aparato)
editar("quipu/ajustes.py", [(
    '    "personaje_escondido": False,  # True = solo la Q en la bandeja, sin personaje en el escritorio\n',
    '    "personaje_escondido": False,  # True = solo la Q en la bandeja, sin personaje en el escritorio\n'
    '    "ultima_sincronizacion": 0,    # cuándo se sincronizó con Drive por última vez (0 = nunca)\n',
)], marca="ultima_sincronizacion")

# 2. google_drive.py: si nadie termina de entrar con Google, dejar de esperar a los 3 minutos
editar("quipu/sincronizacion/google_drive.py", [(
    '        port=0,\n',
    '        port=0,\n        timeout_seconds=180,\n',
)], marca="timeout_seconds")

# 3. main.py: Ajustes necesita la consola para refrescar Notas y Agenda después de bajar datos
editar("quipu/main.py", [(
    '    modulo_ajustes.novedades = novedades\n',
    '    modulo_ajustes.novedades = novedades\n    modulo_ajustes.consola = consola\n',
)], marca="modulo_ajustes.consola")

# 4. modulos/ajustes.py: botones, sincronización en segundo plano, pantallita y luces
editar("quipu/modulos/ajustes.py", [
    (
        'from modulos.web import PaginaConConsola, VistaWeb, preparar_qwebchannel\n',
        'from modulos.web import PaginaConConsola, VistaWeb, en_segundo_plano, preparar_qwebchannel\n'
        'from sincronizacion import google_drive, motor\n',
    ),
    (
        '            "descargando": bool(self.modulo.novedades and self.modulo.novedades.descargando),\n',
        '            "descargando": bool(self.modulo.novedades and self.modulo.novedades.descargando),\n'
        '            "drive": google_drive.esta_conectado(),\n'
        '            "sincronizando": self.modulo.sincronizando,\n'
        '            "ultima_sincro": a.get("ultima_sincronizacion"),\n',
    ),
    (
        '    @Slot()\n    def actualizar(self):\n',
        '    @Slot()\n    def conectar_drive(self):\n        self.modulo.sincronizar(conectar=True)\n\n'
        '    @Slot()\n    def sincronizar_ahora(self):\n        self.modulo.sincronizar()\n\n'
        '    @Slot()\n    def desconectar_drive(self):\n        self.modulo.desconectar_drive()\n\n'
        '    @Slot()\n    def actualizar(self):\n',
    ),
    (
        '        self.novedades = None            # lo conecta main.py\n',
        '        self.novedades = None            # lo conecta main.py\n'
        '        self.consola = None              # lo conecta main.py\n'
        '        self.sincronizando = False\n',
    ),
    (
        '        if self._ritual == "listo" or self._cambiando:\n            return [False, False, True]\n',
        '        if self._ritual == "listo" or self._cambiando:\n            return [False, False, True]\n'
        '        if self.sincronizando:                                   # semáforo dando vueltas\n'
        '            paso = int(time.monotonic() * 2.5) % 3\n'
        '            return [paso == 0, paso == 1, paso == 2]\n',
    ),
    (
        '        if self.novedades and self.novedades.descargando:\n            return "DESCARGANDO"\n',
        '        if self.novedades and self.novedades.descargando:\n            return "DESCARGANDO"\n'
        '        if self.sincronizando:\n            return "SINCRONIZANDO"\n',
    ),
    (
        '    def al_abrir(self):\n',
        '''    # --- Sincronización con Google Drive --------------------------------------------------
    def _avisar_pagina(self):
        if getattr(self, "puente", None):
            self.puente.cambio.emit(self.puente.estado())

    def sincronizar(self, conectar: bool = False):
        """Sincroniza en segundo plano. Con conectar=True, abre el navegador para entrar con Google."""
        if self.sincronizando:
            return
        self.sincronizando = True
        self._avisar_pagina()
        en_segundo_plano(lambda: motor.sincronizar(permitir_navegador=conectar),
                         lambda resultado, error: self._sincro_termino(resultado, error, conectar), self)

    def _sincro_termino(self, resultado, error, conectar: bool):
        self.sincronizando = False
        estado = (resultado or {}).get("estado")
        if error or estado is None:
            print(f"Sincronización: {error}", flush=True)
            self.evento.emit("piensa", "No pude sincronizar. ¿Hay internet?", "")
        elif estado == "sin_conectar":
            self.evento.emit("piensa", "No pude conectarme con Google", "")
        elif estado == "formato_nuevo":
            self.evento.emit("piensa", "Actualizá Quipu para poder sincronizar", "")
        else:
            ajustes().set("ultima_sincronizacion", time.time())
            self.proceso.emit("Sincronizando", "Listo")
            if conectar:
                self.evento.emit("festeja", "¡Listo! Tus datos ya viajan con vos", "")
            if sum(resultado["bajados"].values()) > 0:
                self._refrescar_pantallas()
        self._avisar_pagina()

    def _refrescar_pantallas(self):
        """Si llegaron datos de otro aparato, Notas y Agenda se vuelven a cargar."""
        if not self.consola:
            return
        for id_modulo in ("notas", "agenda"):
            vista = getattr(self.consola.modulos.get(id_modulo), "vista", None)
            if vista:
                vista.reload()

    def desconectar_drive(self):
        google_drive.desconectar()
        self.evento.emit("sonrie", "Listo, me desconecté de Google", "")
        self._avisar_pagina()

    def al_abrir(self):
''',
    ),
], marca="def sincronizar(self, conectar")

# 5. ajustes.html: la fila de Google Drive en Datos
editar("quipu/web/ajustes/ajustes.html", [(
    '      <button class="tecla" id="btn-carpeta">Abrir carpeta</button>\n    </div>\n',
    '      <button class="tecla" id="btn-carpeta">Abrir carpeta</button>\n    </div>\n'
    '    <div class="fila">\n'
    '      <span class="etiqueta">Google Drive</span>\n'
    '      <button class="tecla" id="btn-drive">Conectar</button>\n'
    '    </div>\n'
    '    <div class="fila" id="fila-sincro" style="display:none">\n'
    '      <span class="ayuda" id="sincro-estado"></span>\n'
    '      <button class="tecla" id="btn-sincro">Sincronizar ahora</button>\n'
    '    </div>\n'
    '    <p class="ayuda" id="drive-ayuda">Guarda una copia de tus notas y tu agenda en tu Drive, '
    'para tenerlas también en el celu.</p>\n',
)], marca="btn-drive")

# 6. ajustes.js: dibujar el estado y los botones
editar("quipu/web/ajustes/ajustes.js", [
    (
        '  else if (b.disabled) { b.disabled = false; b.textContent = "Actualizar"; }\n}\n',
        '  else if (b.disabled) { b.disabled = false; b.textContent = "Actualizar"; }\n'
        '  dibujarDrive(e);\n}\n'
        '''
// --- Google Drive ------------------------------------------------------------------------
function cuando(segundos) {
  if (!segundos) return "Todavía no se sincronizó";
  const f = new Date(segundos * 1000);
  const hora = f.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
  const hoy = new Date().toDateString() === f.toDateString();
  return "Última vez: " + (hoy ? "hoy " + hora : f.toLocaleDateString("es-AR") + " " + hora);
}

function dibujarDrive(e) {
  const conectar = $("btn-drive"), sincro = $("btn-sincro");
  $("fila-sincro").style.display = e.drive ? "" : "none";
  $("drive-ayuda").style.display = e.drive ? "none" : "";
  $("sincro-estado").textContent = cuando(e.ultima_sincro);
  if (e.sincronizando) {
    conectar.disabled = true;
    sincro.disabled = true;
    sincro.textContent = "Sincronizando…";
    if (!e.drive) conectar.textContent = "Esperando a Google…";
  } else {
    conectar.disabled = false;
    sincro.disabled = false;
    sincro.textContent = "Sincronizar ahora";
    if (Date.now() >= confirmarDesconectar) conectar.textContent = e.drive ? "Desconectar" : "Conectar";
  }
  conectado = e.drive;
}
''',
    ),
    (
        '$("btn-carpeta").onclick = () => puente.abrir_carpeta();\n',
        '$("btn-carpeta").onclick = () => puente.abrir_carpeta();\n'
        '''
// Drive: conectar abre el navegador; desconectar pide un segundo toque
let conectado = false;
let confirmarDesconectar = 0;
$("btn-drive").onclick = () => {
  const b = $("btn-drive");
  if (!conectado) { puente.conectar_drive(); return; }
  if (Date.now() < confirmarDesconectar) {
    confirmarDesconectar = 0;
    puente.desconectar_drive();
    return;
  }
  confirmarDesconectar = Date.now() + 3000;
  b.textContent = "¿Seguro? Tocá de nuevo";
  setTimeout(() => { if (conectado) b.textContent = "Desconectar"; }, 3000);
};
$("btn-sincro").onclick = () => puente.sincronizar_ahora();
''',
    ),
], marca="dibujarDrive")

print("\nListo. Abrí Quipu con: python quipu\\main.py")
