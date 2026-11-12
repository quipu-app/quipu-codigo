"""Sincronización automática y nombre de usuario entre aparatos. Se puede correr más de una vez."""
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
    ruta.with_name(ruta.name + ".antes2").write_text(original, encoding="utf-8")
    ruta.write_text(texto, encoding="utf-8")
    print(f"  {ruta}: actualizado (copia en {ruta.name}.antes2)")


# 1. ajustes.py: cuándo cambió el nombre (para saber cuál gana entre aparatos)
editar("quipu/ajustes.py", [(
    '    "ultima_sincronizacion": 0,    # cuándo se sincronizó con Drive por última vez (0 = nunca)\n',
    '    "ultima_sincronizacion": 0,    # cuándo se sincronizó con Drive por última vez (0 = nunca)\n'
    '    "nombre_cambiado": 0,          # cuándo se cambió el nombre (viaja con el nombre a Drive)\n',
)], marca="nombre_cambiado")

# 2. motor.py: el nombre viaja en el archivo, y una "foto" rápida de los datos para notar cambios
editar("quipu/sincronizacion/motor.py", [
    (
        '# ---------- Formato del archivo en Drive ----------\n',
        '''# ---------- Para notar cambios sin sincronizar ----------

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
''',
    ),
    (
        'def _a_archivo(unido):\n    return {\n        "formato": FORMATO,\n',
        'def _a_archivo(unido, perfil):\n    return {\n        "formato": FORMATO,\n        "perfil": perfil,\n',
    ),
    (
        'def sincronizar(permitir_navegador=False):\n',
        'def sincronizar(permitir_navegador=False, perfil=None):\n',
    ),
    (
        '    remoto = _desde_archivo(archivo) if archivo else {}\n',
        '''    remoto = _desde_archivo(archivo) if archivo else {}

    # El nombre de usuario: gana el que se cambió más recientemente
    perfil = perfil or {}
    perfil_drive = (archivo or {}).get("perfil") or {}
    perfil_final, perfil_bajado, subir_perfil = perfil, None, False
    if (perfil_drive.get("nombre_cambiado") or 0) > (perfil.get("nombre_cambiado") or 0):
        perfil_final = perfil_bajado = perfil_drive
    elif (perfil.get("nombre_cambiado") or 0) > (perfil_drive.get("nombre_cambiado") or 0):
        subir_perfil = True
''',
    ),
    (
        '        aplicar(con, para_aplicar)\n',
        '        aplicar(con, para_aplicar)\n        hay_que_subir = hay_que_subir or subir_perfil\n',
    ),
    (
        '            contenido = _a_archivo(unido)\n',
        '            contenido = _a_archivo(unido, perfil_final)\n',
    ),
    (
        '        "tamano_kb": tamano_kb,\n',
        '        "tamano_kb": tamano_kb,\n        "perfil": perfil_bajado,\n',
    ),
], marca="def marca_local")

# 3. modulos/ajustes.py: sincronizar solo, sin pisar lo que estás escribiendo
editar("quipu/modulos/ajustes.py", [
    (
        '        self.sincronizando = False\n',
        '''        self.sincronizando = False
        self._silencioso = False          # True = automática: no muestra nada salvo que lleguen datos
        self.sin_conexion = False
        self._marca = None                # cómo estaban los datos en la última sincronización
        self._marca_inicio = None
        self._cambio_desde = None         # cuándo se notó un cambio todavía sin subir
        self._proxima = time.monotonic() + 10    # la primera, apenas arranca Quipu
        reloj = QTimer(self)
        reloj.timeout.connect(self._revisar_auto)
        reloj.start(5000)                 # cada 5 segundos mira si hay algo para subir
''',
    ),
    (
        '            "ultima_sincro": a.get("ultima_sincronizacion"),\n',
        '            "ultima_sincro": a.get("ultima_sincronizacion"),\n'
        '            "sin_conexion": self.modulo.sin_conexion,\n',
    ),
    (
        '        if self.sincronizando:                                   # semáforo dando vueltas\n'
        '            paso = int(time.monotonic() * 2.5) % 3\n'
        '            return [paso == 0, paso == 1, paso == 2]\n',
        '        if self.sincronizando and not self._silencioso:          # semáforo dando vueltas\n'
        '            paso = int(time.monotonic() * 2.5) % 3\n'
        '            return [paso == 0, paso == 1, paso == 2]\n'
        '        if self.sin_conexion:                                    # amarilla: sin internet, reintenta solo\n'
        '            return [False, True, False]\n',
    ),
    (
        '        if self.sincronizando:\n            return "SINCRONIZANDO"\n',
        '        if self.sincronizando and not self._silencioso:\n            return "SINCRONIZANDO"\n',
    ),
    (
        '        ajustes().set("nombre", nombre)\n',
        '        ajustes().set("nombre", nombre)\n        ajustes().set("nombre_cambiado", time.time())\n',
    ),
    (
        '        QTimer.singleShot(2000, QApplication.quit)    # tiempo para que se vea la despedida\n',
        '        QTimer.singleShot(2000, self.salir_sincronizando)    # tiempo para la despedida, y sube lo pendiente\n',
    ),
], marca="def _revisar_auto")

# 3b. modulos/ajustes.py: reemplaza el bloque de sincronización por la versión automática
ruta = Path("quipu/modulos/ajustes.py")
texto = ruta.read_text(encoding="utf-8-sig")
if "def _revisar_auto" not in texto:
    inicio = texto.index("    # --- Sincronización con Google Drive ---")
    fin = texto.index("    def al_abrir(self):")
    texto = texto[:inicio] + '''    # --- Sincronización con Google Drive --------------------------------------------------
    ESPERA_TRAS_CAMBIO = 8        # segundos después de guardar algo
    CADA_CUANTO = 10 * 60         # además, cada 10 minutos (para traer lo que hiciste en el celu)
    REINTENTO = 2 * 60            # si falló (sin internet), reintenta a los 2 minutos

    def _avisar_pagina(self):
        if getattr(self, "puente", None):
            self.puente.cambio.emit(self.puente.estado())

    def sincronizar(self, conectar: bool = False, silencioso: bool = False):
        """Sincroniza en segundo plano. Con conectar=True, abre el navegador para entrar con Google."""
        if self.sincronizando:
            return
        self.sincronizando = True
        self._silencioso = silencioso
        self._marca_inicio = motor.marca_local()
        a = ajustes()
        perfil = {"nombre": a.get("nombre") or "", "nombre_cambiado": a.get("nombre_cambiado") or 0}
        self._avisar_pagina()
        en_segundo_plano(lambda: motor.sincronizar(permitir_navegador=conectar, perfil=perfil),
                         lambda resultado, error: self._sincro_termino(resultado, error, conectar, silencioso),
                         self)

    def _sincro_termino(self, resultado, error, conectar: bool, silencioso: bool):
        self.sincronizando = False
        self._silencioso = False
        estado = (resultado or {}).get("estado")
        ahora = time.monotonic()
        if estado == "listo":
            self.sin_conexion = False
            self._marca = self._marca_inicio       # lo que cambie desde ahora se sube en la próxima
            self._cambio_desde = None
            self._proxima = ahora + self.CADA_CUANTO
            perfil = resultado.get("perfil")
            if perfil:                             # el nombre cambió en otro aparato
                ajustes().set("nombre", perfil.get("nombre") or "")
                ajustes().set("nombre_cambiado", perfil.get("nombre_cambiado") or 0)
            ajustes().set("ultima_sincronizacion", time.time())
            bajados = sum(resultado["bajados"].values())
            if not silencioso or bajados:
                self.proceso.emit("Sincronizando", "Listo")
            if conectar:
                self.evento.emit("festeja", "¡Listo! Tus datos ya viajan con vos", "")
            if bajados:
                self._refrescar_pantallas()
        else:
            self._proxima = ahora + self.REINTENTO
            if error or estado is None:
                print(f"Sincronización: {error}", flush=True)
                self.sin_conexion = True
                if not silencioso:
                    self.evento.emit("piensa", "No pude sincronizar. ¿Hay internet?", "")
            elif not silencioso and estado == "sin_conectar":
                self.evento.emit("piensa", "No pude conectarme con Google", "")
            elif not silencioso and estado == "formato_nuevo":
                self.evento.emit("piensa", "Actualizá Quipu para poder sincronizar", "")
        self._avisar_pagina()

    def _refrescar_pantallas(self):
        """Si llegaron datos de otro aparato, Notas y Agenda se vuelven a cargar."""
        if not self.consola:
            return
        for id_modulo in ("notas", "agenda"):
            vista = getattr(self.consola.modulos.get(id_modulo), "vista", None)
            if vista:
                vista.reload()

    def _editando(self) -> bool:
        """True si Notas o Agenda están en pantalla: ahí no se sincroniza, para no pisar lo que escribís."""
        c = self.consola
        if not c or not c.abierta:
            return False
        actual = c.pantalla.currentWidget()
        return actual is not None and actual in (c.vistas.get("notas"), c.vistas.get("agenda"))

    def _revisar_auto(self):
        """Cada 5 segundos: si algo cambió (o tocó la vuelta de cada 10 minutos), sincroniza."""
        if self.sincronizando or self._saliendo or not google_drive.esta_conectado():
            return
        ahora = time.monotonic()
        if self._marca is not None and self._cambio_desde is None and motor.marca_local() != self._marca:
            self._cambio_desde = ahora
        cambio_listo = self._cambio_desde is not None and ahora - self._cambio_desde >= self.ESPERA_TRAS_CAMBIO
        if (cambio_listo or ahora >= self._proxima) and not self._editando():
            self.sincronizar(silencioso=True)

    def salir_sincronizando(self):
        """Antes de cerrar Quipu, sube lo pendiente (esperando 10 segundos como máximo)."""
        if google_drive.esta_conectado() and (self._marca is None or motor.marca_local() != self._marca):
            self.sincronizar(silencioso=True)
        self._limite_salida = time.monotonic() + 10
        self._esperar_y_salir()

    def _esperar_y_salir(self):
        if self.sincronizando and time.monotonic() < self._limite_salida:
            QTimer.singleShot(300, self._esperar_y_salir)
            return
        QApplication.quit()

    def desconectar_drive(self):
        google_drive.desconectar()
        self.sin_conexion = False
        self.evento.emit("sonrie", "Listo, me desconecté de Google", "")
        self._avisar_pagina()

''' + texto[fin:]
    ruta.write_text(texto, encoding="utf-8")
    print("  quipu/modulos/ajustes.py: bloque de sincronización automática agregado")

# 4. bandeja.py: salir desde la Q también sube lo pendiente
editar("quipu/bandeja.py", [(
    '        self.hide()                                  # que no quede la Q fantasma junto al reloj\n'
    '        QApplication.quit()\n',
    '        self.hide()                                  # que no quede la Q fantasma junto al reloj\n'
    '        modulo_ajustes = self.director.consola.modulos.get("ajustes")\n'
    '        if modulo_ajustes:\n'
    '            modulo_ajustes.salir_sincronizando()     # sube lo pendiente y después cierra\n'
    '        else:\n'
    '            QApplication.quit()\n',
)], marca="salir_sincronizando")

# 5. ajustes.js: avisar si no hay conexión
editar("quipu/web/ajustes/ajustes.js", [(
    '  $("sincro-estado").textContent = cuando(e.ultima_sincro);\n',
    '  $("sincro-estado").textContent = e.sin_conexion ? "Sin conexión: reintento en un rato" : cuando(e.ultima_sincro);\n',
)], marca="sin_conexion")

print("\nListo. Abrí Quipu con: python quipu\\main.py")
