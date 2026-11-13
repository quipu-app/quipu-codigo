// --- Estado -------------------------------------------------------------------
let puente = null;            // las funciones que nos presta Python
let notaActual = null;        // la nota abierta en el editor
let vista = "todo";           // "todo", "sueltas" o "carpetas"
let carpetaAbierta = null;    // id de la carpeta en la que estás adentro, o null
let carpetas = [];            // lista de carpetas, para la grilla y el selector
let cambiado = false;         // ¿hubo cambios sin guardar?
let temporizador = null;      // para el guardado automático
let ultimaBorrada = null;     // para "Deshacer"
let alineacion = 0;

const COLORES = ["#17324D", "#E5484D", "#F2994A", "#27AE60", "#2F80ED", "#9B51E0"];
const COLORES_CARPETA = ["#E5484D", "#F2994A", "#F2C230", "#3BB54A", "#3FA9F5", "#9B7BFF"];
let colorCarpeta = COLORES_CARPETA[0];
let editandoCarpeta = null;   // id de la carpeta que se está editando, o null si se crea una nueva
let confirmarBorrarCarpeta = 0;
const RESALTADO = "#FFF176";
const ALINEACIONES = ["justifyLeft", "justifyCenter", "justifyRight", "justifyFull"];
const ICONOS_ALINEAR = {
  justifyLeft:   [[2, 14], [2, 10], [2, 13], [2, 8]],
  justifyCenter: [[2, 14], [4, 12], [3, 13], [5, 11]],
  justifyRight:  [[2, 14], [6, 14], [3, 14], [8, 14]],
  justifyFull:   [[2, 14], [2, 14], [2, 14], [2, 10]],
};

const $ = (id) => document.getElementById(id);
const escapar = (t) => String(t ?? "").replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// --- Conexión con Python --------------------------------------------------------
try {
  new QWebChannel(qt.webChannelTransport, (canal) => {
    puente = canal.objects.puente;
    console.log("Conectado con Python");
    cargarInicio();
    puente.nube.connect(alNube);
  });
} catch (error) {
  console.log("No se pudo conectar con Python: " + error);
}

// --- Inicio: pestañas, carpetas y lista ------------------------------------------
function cargarInicio() {
  if (!puente) return;
  puente.carpetas((json) => {
    carpetas = JSON.parse(json);
    dibujarPestanas();
    if (vista === "carpetas" && carpetaAbierta === null) {
      dibujarGrilla();
    } else {
      const filtro = carpetaAbierta !== null ? String(carpetaAbierta) : (vista === "sueltas" ? "sin" : "");
      puente.listar(filtro, $("buscar").value, (lista) => dibujarLista(JSON.parse(lista)));
    }
  });
}

function dibujarPestanas() {
  document.querySelectorAll(".pestana").forEach((p) => p.classList.toggle("activa", p.dataset.vista === vista));
  const adentro = carpetaAbierta !== null;
  $("migas").hidden = !adentro;
  if (adentro) {
    const c = carpetas.find((x) => x.id === carpetaAbierta);
    $("nombre-abierta").textContent = c ? c.nombre : "";
    $("punto-abierta").style.background = c ? c.color : "transparent";
  }
  const verGrilla = vista === "carpetas" && !adentro;
  $("grilla").hidden = !verGrilla;
  $("lista").hidden = verGrilla;
}

function cambiarVista(nueva) {
  vista = nueva;
  carpetaAbierta = null;
  cargarInicio();
}

function dibujarGrilla() {
  $("vacio").hidden = carpetas.length > 0;
  $("vacio").textContent = "Todavía no hay carpetas. Tocá «+ Carpeta» para crear la primera.";
  $("grilla").innerHTML = carpetas.map((c) => `
    <button class="carpeta" data-id="${c.id}" style="border-top-color:${c.color}">
      <b>${escapar(c.nombre)}</b>
      <small>${c.cantidad} ${c.cantidad === 1 ? "nota" : "notas"}</small>
    </button>`).join("");
  $("grilla").querySelectorAll(".carpeta").forEach((tarjeta) => {
    tarjeta.onclick = () => { carpetaAbierta = Number(tarjeta.dataset.id); cargarInicio(); };
  });
  activarArrastreGrilla();
}

function dibujarLista(notas) {
  $("vacio").hidden = notas.length > 0;
  $("vacio").textContent = carpetaAbierta !== null ? "Esta carpeta está vacía. Tocá «+ Nota» para escribir una."
    : vista === "sueltas" ? "No hay notas sueltas: todas están en alguna carpeta."
    : "Todavía no hay notas. Tocá «+ Nota» para escribir la primera.";
  $("lista").innerHTML = notas.map((n) => `
    <div class="nota" data-id="${n.id}">
      <span class="punto" style="background:${n.color || "transparent"}"></span>
      <div class="cuerpo">
        <b>${n.fijada ? "★ " : ""}${escapar(n.titulo)}${n.compartida ? '<span class="compartida">👥</span>' : ""}</b>
        <span class="resumen">${escapar(n.resumen)}</span>
      </div>
      <span class="fecha">${n.fecha}</span>
    </div>`).join("");
  $("lista").querySelectorAll(".nota").forEach((el) => {
    el.onclick = () => abrirNota(Number(el.dataset.id));
  });
  activarArrastre();
}

function mostrar(pantalla) {
  $("inicio").hidden = pantalla !== "inicio";
  $("editor").hidden = pantalla !== "editor";
  $("paleta").hidden = true;
  $("menu-carpetas").hidden = true;
}

// --- Abrir, crear y guardar -----------------------------------------------------
function limpiarHtml(html) {
  // Las notas de la versión anterior traen un documento completo: nos quedamos con el cuerpo
  if (!html) return "";
  if (/<html/i.test(html)) return new DOMParser().parseFromString(html, "text/html").body.innerHTML;
  return html;
}

function cargarEnEditor(nota) {
  notaActual = nota;
  $("titulo").value = nota.titulo || "";
  $("texto").innerHTML = limpiarHtml(nota.html);
  $("btn-fijar").classList.toggle("activa", !!nota.fijada);
  dibujarSelectorCarpeta();
  cambiado = false;
  mostrar("editor");
}

function abrirNota(id) {
  puente.abrir(id, (json) => cargarEnEditor(JSON.parse(json)));
}

function nuevaNota() {
  cargarEnEditor({ id: null, titulo: "", html: "", fijada: false, carpeta_id: carpetaAbierta, codigo: "" });
  $("titulo").focus();
}

function marcarCambio() {
  // Guardado automático: guarda en silencio 1,5 segundos después de la última tecla
  cambiado = true;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => guardar(false), 1500);
}

function guardar(avisar, alTerminar) {
  clearTimeout(temporizador);
  if (!cambiado || !puente) { if (alTerminar) alTerminar(); return; }
  const datos = {
    id: notaActual.id,
    titulo: $("titulo").value,
    html: $("texto").innerHTML,
    texto: $("texto").innerText,
    carpeta_id: notaActual.carpeta_id ?? null,
  };
  cambiado = false;
  puente.guardar(JSON.stringify(datos), avisar, (id) => {
    if (id > 0) notaActual.id = id;
    if (alTerminar) alTerminar();
  });
}

function volver() {
  guardar(true, () => { mostrar("inicio"); cargarInicio(); });
}

// --- Fijar y borrar -------------------------------------------------------------
function fijar() {
  const aplicar = () => {
    if (!notaActual.id) return;
    notaActual.fijada = !notaActual.fijada;
    $("btn-fijar").classList.toggle("activa", notaActual.fijada);
    puente.fijar(notaActual.id, notaActual.fijada);
  };
  if (!notaActual.id) { cambiado = true; guardar(false, aplicar); } else aplicar();
}

function borrar() {
  clearTimeout(temporizador);
  cambiado = false;
  if (!notaActual.id) { mostrar("inicio"); return; }
  ultimaBorrada = notaActual.id;
  puente.borrar(notaActual.id, () => {
    mostrar("inicio");
    cargarInicio();
    $("aviso").hidden = false;
    setTimeout(() => { $("aviso").hidden = true; }, 6000);
  });
}

function deshacer() {
  if (ultimaBorrada === null) return;
  puente.restaurar(ultimaBorrada, () => {
    ultimaBorrada = null;
    $("aviso").hidden = true;
    cargarInicio();
  });
}

// --- Carpeta de la nota ----------------------------------------------------------
function dibujarSelectorCarpeta() {
  const actual = notaActual.carpeta_id ?? null;
  const marca = (id) => (id === actual ? ' class="actual"' : "");
  $("menu-carpetas").innerHTML =
    `<small class="menu-titulo">¿Dónde la guardo?</small>` +
    `<button data-id=""${marca(null)}>Suelta, sin carpeta</button>` +
    carpetas.map((x) => `<button data-id="${x.id}"${marca(x.id)}><span class="punto" style="background:${x.color}"></span>${escapar(x.nombre)}</button>`).join("");
  $("menu-carpetas").querySelectorAll("button").forEach((b) => {
    b.onclick = () => {
      const elegida = b.dataset.id ? Number(b.dataset.id) : null;
      if (elegida !== (notaActual.carpeta_id ?? null)) { notaActual.carpeta_id = elegida; cambiado = true; }
      $("menu-carpetas").hidden = true;
      volver();                                   // guarda en esa carpeta y vuelve a la lista
    };
  });
}

// --- Formato -----------------------------------------------------------------------
function comando(cmd, valor = null) {
  $("texto").focus();
  document.execCommand(cmd, false, valor);
  marcarCambio();
  actualizarTeclas();
}

function actualizarTeclas() {
  document.querySelectorAll("[data-cmd]").forEach((b) => {
    b.classList.toggle("activa", document.queryCommandState(b.dataset.cmd));
  });
}

function cambiarTamano(paso) {
  const actual = Number(document.queryCommandValue("fontSize")) || 3;   // tamaños de 1 a 7
  comando("fontSize", String(Math.max(1, Math.min(7, actual + paso))));
}

function resaltar() {
  const yaResaltado = document.queryCommandValue("backColor") === "rgb(255, 241, 118)";
  comando("hiliteColor", yaResaltado ? "transparent" : RESALTADO);
}

function insertarCasilla() {
  comando("insertHTML", '<span class="caja" contenteditable="false">☐</span>&nbsp;');
}

function dibujarIconoAlinear() {
  const lineas = ICONOS_ALINEAR[ALINEACIONES[alineacion]]
    .map(([x1, x2], i) => `<line x1="${x1}" y1="${3 + i * 3.4}" x2="${x2}" y2="${3 + i * 3.4}"/>`).join("");
  $("btn-alinear").innerHTML =
    `<svg viewBox="0 0 16 16" width="15" height="15" stroke="#2B2B33" stroke-width="1.6" stroke-linecap="round">${lineas}</svg>`;
}

function alinear() {
  alineacion = (alineacion + 1) % ALINEACIONES.length;
  dibujarIconoAlinear();
  comando(ALINEACIONES[alineacion]);
}

function insertarImagen() {
  const seleccion = window.getSelection();
  const rango = seleccion.rangeCount ? seleccion.getRangeAt(0).cloneRange() : null;
  puente.elegir_imagen((datos) => {
    if (!datos) return;
    const texto = $("texto");
    texto.focus();
    seleccion.removeAllRanges();
    if (rango && texto.contains(rango.startContainer)) {
      seleccion.addRange(rango);
    } else {
      const alFinal = document.createRange();
      alFinal.selectNodeContents(texto);
      alFinal.collapse(false);
      seleccion.addRange(alFinal);
    }
    comando("insertHTML", `<img src="${datos}">`);
  });
}

// --- QR y TXT -------------------------------------------------------------------
// --- Colaborar ---------------------------------------------------------------------
function abrirColaborar() {
  $("colab-mensaje").textContent = "";
  $("colab-entrada").value = "";
  dibujarColaborar();
  $("panel-colab").hidden = false;
}

function dibujarColaborar() {
  const codigo = notaActual && notaActual.codigo;
  $("colab-codigo").hidden = !codigo;
  $("colab-opciones").hidden = !!codigo;
  if (codigo) $("colab-mostrar").textContent = codigo.slice(0, 4) + "-" + codigo.slice(4);
}

function generarCodigo() {
  $("colab-mensaje").textContent = "Generando…";
  const pedir = () => {
    if (!notaActual.id) { $("colab-mensaje").textContent = "Escribí algo antes de compartir"; return; }
    puente.compartir(notaActual.id);
  };
  if (!notaActual.id) cambiado = true;
  guardar(false, pedir);
}

function unirme() {
  const texto = $("colab-entrada").value.trim();
  if (!texto) { $("colab-entrada").focus(); return; }
  $("colab-mensaje").textContent = "Buscando…";
  puente.unirse(texto);
}

function copiarCodigo() {
  const t = document.createElement("textarea");
  t.value = $("colab-mostrar").textContent;
  document.body.appendChild(t);
  t.select();
  document.execCommand("copy");
  t.remove();
  $("colab-mensaje").textContent = "¡Copiado!";
}

function alNube(json) {
  const r = JSON.parse(json);
  if (r.tipo === "error") { $("colab-mensaje").textContent = r.mensaje; return; }
  if (r.tipo === "codigo" && notaActual && notaActual.id === r.id) {
    notaActual.codigo = r.codigo;
    $("colab-mensaje").textContent = "";
    dibujarColaborar();
  }
  if (r.tipo === "unida") {
    $("panel-colab").hidden = true;
    guardar(false, () => abrirNota(r.id));
  }
  if (r.tipo === "actualizada" && notaActual && notaActual.id === r.id && !cambiado) {
    $("titulo").value = r.titulo || "";
    $("texto").innerHTML = limpiarHtml(r.html);
  }
}

function textoParaCompartir() {
  const titulo = $("titulo").value.trim();
  const cuerpo = $("texto").innerText.trim();
  return titulo ? `${titulo}\n\n${cuerpo}` : cuerpo;
}

function verQr() {
  const texto = textoParaCompartir();
  $("img-qr").hidden = true;
  $("panel-qr").hidden = false;
  if (!texto) { $("texto-qr").textContent = "La nota está vacía"; return; }
  $("texto-qr").textContent = "Generando…";
  puente.generar_qr(texto, (imagen) => {
    if (!imagen) {
      $("texto-qr").textContent = "La nota es muy larga para un QR. Pronto vas a poder pasarla al celu por WiFi.";
      return;
    }
    $("img-qr").src = imagen;
    $("img-qr").hidden = false;
    $("texto-qr").textContent = "Escaneá con el celu";
  });
}

function exportarTxt() {
  const texto = textoParaCompartir();
  if (!texto) return;
  puente.exportar_txt($("titulo").value.trim(), texto);
}

// --- Crear carpetas -----------------------------------------------------------------
function abrirPanelCarpeta() {
  editandoCarpeta = null;
  $("btn-crear-carpeta").textContent = "Crear";
  $("panel-carpeta").hidden = false;
  $("nombre-carpeta").value = "";
  colorCarpeta = COLORES_CARPETA[carpetas.length % COLORES_CARPETA.length];   // propone el siguiente color
  dibujarColoresCarpeta();
  $("nombre-carpeta").focus();
}

function dibujarColoresCarpeta() {
  $("colores-carpeta").innerHTML = COLORES_CARPETA.map((c) =>
    `<button data-color="${c}" class="${c === colorCarpeta ? "elegido" : ""}" style="background:${c}"></button>`).join("");
  $("colores-carpeta").querySelectorAll("button").forEach((b) => {
    b.onclick = () => { colorCarpeta = b.dataset.color; dibujarColoresCarpeta(); };
  });
}

function crearCarpeta() {
  const nombre = $("nombre-carpeta").value.trim();
  if (!nombre) { $("nombre-carpeta").focus(); return; }
  if (editandoCarpeta !== null) {
    puente.editar_carpeta(editandoCarpeta, nombre, colorCarpeta, () => {
      $("panel-carpeta").hidden = true;
      editandoCarpeta = null;
      cargarInicio();
    });
    return;
  }
  puente.crear_carpeta(nombre, colorCarpeta, () => {
    $("panel-carpeta").hidden = true;
    cambiarVista("carpetas");                 // te lleva a ver la carpeta nueva
  });
}

// --- Editar y borrar la carpeta abierta ---------------------------------------------
function abrirEditarCarpeta() {
  const c = carpetas.find((x) => x.id === carpetaAbierta);
  if (!c) return;
  editandoCarpeta = c.id;
  $("btn-crear-carpeta").textContent = "Guardar";
  $("panel-carpeta").hidden = false;
  $("nombre-carpeta").value = c.nombre;
  colorCarpeta = c.color;
  dibujarColoresCarpeta();
  $("nombre-carpeta").focus();
}

function borrarCarpeta() {
  const boton = $("btn-borrar-carpeta");
  if (Date.now() > confirmarBorrarCarpeta) {          // primer toque: pide confirmar
    confirmarBorrarCarpeta = Date.now() + 3000;
    boton.textContent = "¿Seguro? Tocá de nuevo";
    setTimeout(() => { boton.textContent = "Borrar"; }, 3000);
    return;
  }
  confirmarBorrarCarpeta = 0;
  boton.textContent = "Borrar";
  puente.borrar_carpeta(carpetaAbierta, () => {
    $("panel-carpeta").hidden = true;
    cambiarVista("carpetas");
  });
}

// --- Reordenar arrastrando -----------------------------------------------------------
function arrastrable(contenedor, selector, alSoltar) {
  let arrastrado = null;
  contenedor.querySelectorAll(selector).forEach((el) => {
    el.draggable = true;
    el.addEventListener("dragstart", () => { arrastrado = el; el.classList.add("arrastrando"); });
    el.addEventListener("dragend", () => { el.classList.remove("arrastrando"); arrastrado = null; });
    el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("sobre"); });
    el.addEventListener("dragleave", () => el.classList.remove("sobre"));
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.classList.remove("sobre");
      if (!arrastrado || arrastrado === el) return;
      contenedor.insertBefore(arrastrado, el);
      alSoltar([...contenedor.querySelectorAll(selector)].map((x) => Number(x.dataset.id)));
    });
  });
}

function activarArrastre() {
  arrastrable($("lista"), ".nota", (ids) => puente.ordenar(JSON.stringify(ids)));
}

function activarArrastreGrilla() {
  arrastrable($("grilla"), ".carpeta", (ids) => puente.ordenar_carpetas(JSON.stringify(ids)));
}

// --- Eventos -------------------------------------------------------------------
$("buscar").addEventListener("input", () => cargarInicio());
$("titulo").addEventListener("input", marcarCambio);
$("texto").addEventListener("input", marcarCambio);
$("texto").addEventListener("keyup", actualizarTeclas);
$("texto").addEventListener("mouseup", actualizarTeclas);
$("texto").addEventListener("click", (e) => {
  if (e.target.classList.contains("caja")) {          // tildar o destildar una casilla
    const hecha = e.target.classList.toggle("hecha");
    e.target.textContent = hecha ? "☑" : "☐";
    marcarCambio();
  }
});

// Que las teclas de formato no le saquen el cursor al texto
$("barra").addEventListener("mousedown", (e) => e.preventDefault());
$("paleta").addEventListener("mousedown", (e) => e.preventDefault());

document.querySelectorAll("[data-cmd]").forEach((b) => { b.onclick = () => comando(b.dataset.cmd); });
document.querySelectorAll(".pestana").forEach((p) => { p.onclick = () => cambiarVista(p.dataset.vista); });
$("btn-salir-carpeta").onclick = () => { carpetaAbierta = null; cargarInicio(); };
$("btn-menos").onclick = () => cambiarTamano(-1);
$("btn-mas").onclick = () => cambiarTamano(1);
$("btn-color").onclick = () => { $("paleta").hidden = !$("paleta").hidden; };
$("btn-resaltar").onclick = resaltar;
$("btn-casilla").onclick = insertarCasilla;
$("btn-alinear").onclick = alinear;
$("btn-imagen").onclick = insertarImagen;

$("paleta").innerHTML = COLORES.map((c) => `<button data-color="${c}" style="background:${c}"></button>`).join("");
$("paleta").querySelectorAll("button").forEach((b) => {
  b.onclick = () => { comando("foreColor", b.dataset.color); $("paleta").hidden = true; };
});

$("btn-listo").onclick = () => { dibujarSelectorCarpeta(); $("menu-carpetas").hidden = !$("menu-carpetas").hidden; };
$("btn-nueva").onclick = nuevaNota;
$("btn-volver").onclick = volver;
$("btn-fijar").onclick = fijar;
$("btn-borrar").onclick = borrar;
$("btn-deshacer").onclick = deshacer;
$("btn-qr").onclick = verQr;
$("btn-txt").onclick = exportarTxt;
$("btn-cerrar-qr").onclick = () => { $("panel-qr").hidden = true; };
$("btn-carpeta-nueva").onclick = abrirPanelCarpeta;
$("btn-cancelar-carpeta").onclick = () => { $("panel-carpeta").hidden = true; };
$("btn-crear-carpeta").onclick = crearCarpeta;
$("btn-editar-carpeta").onclick = abrirEditarCarpeta;
$("btn-borrar-carpeta").onclick = borrarCarpeta;
$("nombre-carpeta").addEventListener("keydown", (e) => { if (e.key === "Enter") crearCarpeta(); });
$("btn-colaborar").onclick = abrirColaborar;
$("btn-generar").onclick = generarCodigo;
$("btn-unirme").onclick = unirme;
$("btn-copiar-codigo").onclick = copiarCodigo;
$("btn-cerrar-colab").onclick = () => { $("panel-colab").hidden = true; };
$("colab-entrada").addEventListener("keydown", (e) => { if (e.key === "Enter") unirme(); });

// Con una nota compartida abierta, cada 10 segundos se fija si la otra persona la cambió
setInterval(() => {
  if (puente && notaActual && notaActual.id && notaActual.codigo && !$("editor").hidden && !cambiado) {
    puente.revisar_nube(notaActual.id);
  }
}, 10000);

dibujarIconoAlinear();