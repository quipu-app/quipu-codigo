import base64
import io
import json
import time
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QFileDialog

import config
import nube
from almacen import Almacen
from modulos.base import Modulo
from modulos.web import PaginaConConsola, VistaWeb, en_segundo_plano, preparar_qwebchannel

CARPETA = config.CARPETA_WEB / "notas"


class Puente(QObject):
    """Las funciones que Python le presta a la página de Notas."""
    nube = Signal(str)   # respuestas de la nube: código generado, nota unida, cambios o errores

    def __init__(self, modulo):
        super().__init__()
        self.modulo = modulo
        self.almacen = modulo.almacen

    # --- Lista y carpetas ------------------------------------------------------------
    @Slot(str, str, result=str)
    def listar(self, carpeta: str, buscar: str) -> str:
        """carpeta: "" = todas, "sin" = solo las sueltas, o el id de una carpeta."""
        if carpeta == "sin":
            filas = [n for n in self.almacen.notas(None, buscar.strip()) if n["carpeta_id"] is None]
        else:
            filas = self.almacen.notas(int(carpeta) if carpeta else None, buscar.strip())
        notas = []
        for n in filas:
            lineas = [l for l in n["texto"].split("\n") if l.strip()]
            titulo = n["titulo"] or (lineas[0][:40] if lineas else "Sin título")
            resto = lineas if n["titulo"] else lineas[1:]
            notas.append({
                "id": n["id"],
                "titulo": titulo,
                "resumen": " ".join(resto)[:80],
                "fecha": time.strftime("%d/%m", time.localtime(n["modificada"])),
                "color": self.almacen.color_carpeta(n["carpeta_id"]),
                "fijada": bool(n["fijada"]),
                "compartida": bool(n["codigo"]),
            })
        return json.dumps(notas, ensure_ascii=False)

    @Slot(result=str)
    def carpetas(self) -> str:
        return json.dumps([
            {"id": c["id"], "nombre": c["nombre"], "color": c["color"],
             "cantidad": self.almacen.contar_notas(c["id"])}
            for c in self.almacen.carpetas()
        ], ensure_ascii=False)

    # --- Una nota ------------------------------------------------------------------------
    @Slot(int, result=str)
    def abrir(self, nota_id: int) -> str:
        n = self.almacen.nota(nota_id)
        return json.dumps({
            "id": n["id"], "titulo": n["titulo"] or "", "html": n["html"],
            "carpeta_id": n["carpeta_id"], "fijada": bool(n["fijada"]), "codigo": n["codigo"] or "",
        }, ensure_ascii=False)

    @Slot(str, bool, result=int)
    def guardar(self, datos: str, avisar: bool) -> int:
        d = json.loads(datos)
        if d.get("id") is None and not d["titulo"].strip() and not d["texto"].strip():
            return -1                                  # no guardamos notas nuevas vacías
        nota_id = self.almacen.guardar_nota(d.get("id"), d["titulo"].strip(), d["html"],
                                            d["texto"], d.get("carpeta_id"))
        if avisar:
            self.modulo.guardado.emit()                # "Guardando…" en la pantallita
        self.modulo.subir_si_compartida(nota_id)
        return nota_id

    @Slot(int, bool)
    def fijar(self, nota_id: int, fijada: bool):
        self.almacen.fijar(nota_id, fijada)

    @Slot(int)
    def borrar(self, nota_id: int):
        self.almacen.borrar(nota_id, True)

    @Slot(int)
    def restaurar(self, nota_id: int):
        self.almacen.borrar(nota_id, False)

    # --- Imagen, QR y TXT ----------------------------------------------------------------
    @Slot(result=str)
    def elegir_imagen(self) -> str:
        """Elige una imagen y la devuelve "metida" en texto, lista para guardarse dentro de la nota."""
        ruta, _ = QFileDialog.getOpenFileName(
            self.modulo.vista.window(), "Agregar imagen", str(Path.home() / "Pictures"),
            "Imágenes (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        if not ruta:
            return ""
        imagen = QImage(ruta)
        if imagen.isNull():
            return ""
        if imagen.width() > 1000:                        # achicamos las fotos grandes para que no pesen
            imagen = imagen.scaledToWidth(1000, Qt.SmoothTransformation)
        datos = QByteArray()
        buffer = QBuffer(datos)
        buffer.open(QIODevice.WriteOnly)
        imagen.save(buffer, "JPG", 85)
        self.modulo.evento.emit("sonrie", "imagen_lista", "")
        self.modulo.aviso.emit("Las fotos quedan en Quipu: no viajan en el TXT ni en el QR")
        return "data:image/jpeg;base64," + base64.b64encode(bytes(datos)).decode()

    @Slot(str, result=str)
    def generar_qr(self, texto: str) -> str:
        """Genera el QR de la nota y lo devuelve como imagen en texto, o "" si es muy larga."""
        if len(texto) > 900:
            return ""
        self.modulo.proceso.emit("Generando QR", "Generado")
        import qrcode
        qr = qrcode.QRCode(border=2, box_size=4)
        qr.add_data(texto)
        buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
        self.modulo.evento.emit("sonrie", "qr_listo", "")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    @Slot(str, str)
    def exportar_txt(self, titulo: str, texto: str):
        """Abre la ventana de Windows para elegir dónde guardar la nota como archivo de texto."""
        nombre = (titulo or texto.split("\n", 1)[0])[:40].strip() or "nota"
        for caracter in '\\/:*?"<>|':                     # caracteres que Windows no permite en nombres
            nombre = nombre.replace(caracter, "")
        sugerido = Path.home() / "Documents" / f"{nombre}.txt"
        ruta, _ = QFileDialog.getSaveFileName(
            self.modulo.vista.window(), "Exportar nota", str(sugerido), "Texto (*.txt)")
        if ruta:
            self.modulo.proceso.emit("Exportando", "Exportado")
            Path(ruta).write_text(texto, encoding="utf-8")
            self.modulo.evento.emit("sonrie", "txt_listo", "")
    @Slot(str, str, result=int)
    def crear_carpeta(self, nombre: str, color: str) -> int:
        nombre = nombre.strip()
        if not nombre:
            return -1
        carpeta_id = self.almacen.crear_carpeta(nombre, color)
        self.modulo.proceso.emit("Creando carpeta", "Creada")
        return carpeta_id

    @Slot(int, str, str, result=bool)
    def editar_carpeta(self, carpeta_id: int, nombre: str, color: str) -> bool:
        nombre = nombre.strip()
        if not nombre:
            return False
        self.almacen.editar_carpeta(carpeta_id, nombre, color)
        self.modulo.proceso.emit("Guardando carpeta", "Guardada")
        return True

    @Slot(int)
    def borrar_carpeta(self, carpeta_id: int):
        self.almacen.borrar_carpeta(carpeta_id)
        self.modulo.proceso.emit("Borrando carpeta", "Borrada")

    @Slot(str)
    def ordenar(self, ids_json: str):
        """Guarda el orden de las notas después de arrastrarlas."""
        self.almacen.ordenar_notas(json.loads(ids_json))

    @Slot(str)
    def ordenar_carpetas(self, ids_json: str):
        """Guarda el orden de las carpetas después de arrastrarlas."""
        self.almacen.ordenar_carpetas(json.loads(ids_json))

    # --- Colaborar ------------------------------------------------------------------------
    @Slot(int)
    def compartir(self, nota_id: int):
        self.modulo.compartir(nota_id)

    @Slot(str)
    def unirse(self, codigo: str):
        self.modulo.unirse(codigo)

    @Slot(int)
    def revisar_nube(self, nota_id: int):
        self.modulo.revisar_nube(nota_id)

class Notas(Modulo):
    id = "notas"
    titulo = "Notas"

    def __init__(self):
        super().__init__()
        self.almacen = Almacen()
        self.vista = None
        self.puente = None
        self._revisando = False          # para no pedir cambios a la nube dos veces a la vez

    def crear_vista(self):
        preparar_qwebchannel(CARPETA)
        self.vista = VistaWeb()
        self.pagina = PaginaConConsola("notas", self.vista)
        self.vista.setPage(self.pagina)
        self.pagina.setBackgroundColor(Qt.transparent)   # las esquinas redondeadas las pone el CSS

        self.puente = Puente(self)
        self.canal = QWebChannel(self.pagina)
        self.canal.registerObject("puente", self.puente)
        self.pagina.setWebChannel(self.canal)

        self.vista.setUrl(QUrl.fromLocalFile(str(CARPETA / "notas.html")))
        return self.vista

    # --- Colaborar ----------------------------------------------------------------------
    def _responder(self, **datos):
        if self.puente:
            self.puente.nube.emit(json.dumps(datos, ensure_ascii=False))

    def compartir(self, nota_id: int):
        n = self.almacen.nota(nota_id)
        if not n:
            return
        if n["codigo"]:
            self._responder(tipo="codigo", id=nota_id, codigo=n["codigo"])
            return
        titulo, html, texto = n["titulo"], n["html"], n["texto"]
        self.proceso.emit("Compartiendo", "Compartida")

        def trabajo():
            codigo = nube.codigo_libre()
            return codigo, nube.subir(codigo, titulo, html, texto)

        def al_terminar(resultado, error):
            if error:
                self._responder(tipo="error", mensaje=nube.mensaje(error))
                return
            codigo, cambiado = resultado
            self.almacen.marcar_compartida(nota_id, codigo, cambiado)
            self.evento.emit("festeja", "¡Lista para compartir!", "")
            self._responder(tipo="codigo", id=nota_id, codigo=codigo)

        en_segundo_plano(trabajo, al_terminar, self)

    def unirse(self, texto: str):
        codigo = nube.normalizar(texto)
        if len(codigo) != 8:
            self._responder(tipo="error", mensaje="El código tiene 8 letras y números")
            return
        existente = self.almacen.nota_por_codigo(codigo)
        if existente:
            self._responder(tipo="unida", id=existente["id"])
            return
        self.proceso.emit("Buscando", "Encontrada")

        def al_terminar(d, error):
            if error:
                self._responder(tipo="error", mensaje=nube.mensaje(error))
                return
            if d is None:
                self._responder(tipo="error", mensaje="No encontré ninguna nota con ese código")
                return
            nota_id = self.almacen.guardar_nota(None, d.get("titulo", ""), d.get("html", ""),
                                                d.get("texto", ""), None)
            self.almacen.marcar_compartida(nota_id, codigo, d["cambiado"])
            self.evento.emit("festeja", "¡Ya están conectados!", "")
            self._responder(tipo="unida", id=nota_id)

        en_segundo_plano(lambda: nube.bajar(codigo), al_terminar, self)

    def revisar_nube(self, nota_id: int):
        n = self.almacen.nota(nota_id)
        if not n or not n["codigo"] or self._revisando:
            return
        self._revisando = True
        codigo, visto = n["codigo"], n["remoto"] or 0

        def al_terminar(d, error):
            self._revisando = False
            if error or not d or d["cambiado"] <= visto + 0.001:
                return                                   # sin cambios nuevos (o sin internet)
            self.almacen.actualizar_desde_nube(nota_id, d.get("titulo", ""), d.get("html", ""),
                                               d.get("texto", ""), d["cambiado"])
            self._responder(tipo="actualizada", id=nota_id, titulo=d.get("titulo", ""),
                            html=d.get("html", ""))
            self.aviso.emit("Nota compartida actualizada")

        en_segundo_plano(lambda: nube.bajar(codigo), al_terminar, self)

    def subir_si_compartida(self, nota_id: int):
        n = self.almacen.nota(nota_id)
        if not n or not n["codigo"]:
            return
        codigo, titulo, html, texto = n["codigo"], n["titulo"], n["html"], n["texto"]

        def al_terminar(cambiado, error):
            if error:
                self.aviso.emit("No pude subir la nota compartida: " + nube.mensaje(error))
                return
            self.almacen.marcar_compartida(nota_id, codigo, cambiado)

        en_segundo_plano(lambda: nube.subir(codigo, titulo, html, texto), al_terminar, self)