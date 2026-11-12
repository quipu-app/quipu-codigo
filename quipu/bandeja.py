"""El ícono de Quipu en la bandeja de Windows (junto al reloj) y su menú."""
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import config
from ajustes import ajustes


class Bandeja(QSystemTrayIcon):
    def __init__(self, director):
        super().__init__(QIcon(str(config.BASE / "assets" / "marca" / "q.png")))
        self.director = director
        self.personaje = director.personaje
        self.consola = director.consola
        self.setToolTip("Quipu")

        # El menú: el mismo para el click derecho en la Q y en el personaje
        self.menu = QMenu()
        self.accion_personaje = QAction("Esconder personaje", self.menu)
        self.accion_personaje.triggered.connect(self.alternar_personaje)
        accion_abrir = QAction("Abrir Quipu", self.menu)
        accion_abrir.triggered.connect(self.abrir)
        accion_salir = QAction("Salir de Quipu", self.menu)
        accion_salir.triggered.connect(self.salir)
        self.menu.addAction(self.accion_personaje)
        self.menu.addAction(accion_abrir)
        self.menu.addSeparator()
        self.menu.addAction(accion_salir)
        self.menu.aboutToShow.connect(self.actualizar_menu)
        self.setContextMenu(self.menu)

        self.activated.connect(self.al_activar)
        self.personaje.al_click_derecho = self.menu_en              # click derecho sobre el personaje
        director.bandeja = self                                      # para los avisos con el personaje escondido
        self.show()
        if ajustes().get("personaje_escondido"):
            self.personaje.hide()

    # --- El menú -------------------------------------------------------------------------
    def actualizar_menu(self):
        visible = self.personaje.isVisible()
        self.accion_personaje.setText("Esconder personaje" if visible else "Mostrar personaje")

    def menu_en(self, posicion):
        self.actualizar_menu()
        self.menu.popup(posicion)

    def al_activar(self, motivo):
        """Un click en la Q: abre o cierra la consola."""
        if motivo == QSystemTrayIcon.ActivationReason.Trigger:
            if self.consola.abierta:
                self.director.cerrar_consola()
            else:
                self.abrir()

    # --- Esconder y mostrar --------------------------------------------------------------
    def alternar_personaje(self):
        if self.personaje.isVisible():
            self.esconder()
        else:
            self.mostrar()

    def esconder(self):
        if self.director.en_bienvenida:
            return                                   # en la bienvenida, el anfitrión no se va
        ajustes().set("personaje_escondido", True)
        self.personaje.globo.hide()
        if self.consola.abierta:
            self.director.cerrar_consola()           # primero vuelve a su lugar...
            QTimer.singleShot(1000, self.personaje.hide)   # ...y después desaparece
        else:
            self.personaje.hide()
        self.avisar("Sigo acá: tocá la Q para volver a verme")

    def mostrar(self):
        ajustes().set("personaje_escondido", False)
        self.personaje.show()

    def abrir(self):
        if not self.personaje.isVisible():
            self.mostrar()
        if not self.consola.abierta:
            self.director.abrir_consola()

    # --- Avisos y salida -----------------------------------------------------------------
    def avisar(self, texto: str):
        """Notificación de Windows desde la Q (cuando no hay personaje que lo diga)."""
        self.showMessage("Quipu", texto, self.icon(), 6000)

    def salir(self):
        if self.personaje.isVisible():
            self.personaje.decir("saluda", "ajustes_chau")
            QTimer.singleShot(1500, self._cerrar)    # tiempo para que se vea la despedida
        else:
            self._cerrar()

    def _cerrar(self):
        self.hide()                                  # que no quede la Q fantasma junto al reloj
        modulo_ajustes = self.director.consola.modulos.get("ajustes")
        if modulo_ajustes:
            modulo_ajustes.salir_sincronizando()     # sube lo pendiente y después cierra
        else:
            QApplication.quit()
