// --- Estado -------------------------------------------------------------------
let puente = null;
let anio, mes;              // el mes que se está viendo
let elegido;                // el día elegido, "AAAA-MM-DD"
let editando = null;        // el evento que se edita, o null si es nuevo
let form = {};              // lo elegido en el formulario
let pregunta = null;        // el evento que espera "¿se hizo?"

const $ = (id) => document.getElementById(id);
const escapar = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const iso = (a, m, d) => `${a}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

const AVISOS = [[0, "No"], [5, "5'"], [10, "10'"], [30, "30'"]];
const REPETIR = [["no", "No"], ["dia", "Día"], ["semana", "Semana"], ["mes", "Mes"], ["anio", "Año"]];
const COLORES = ["#E5484D", "#F2994A", "#F2C230", "#3BB54A", "#3FA9F5", "#9B7BFF"];

// --- Conexión con Python --------------------------------------------------------
try {
  new QWebChannel(qt.webChannelTransport, (canal) => {
    puente = canal.objects.puente;
    const hoy = new Date();
    anio = hoy.getFullYear(); mes = hoy.getMonth() + 1;
    elegido = iso(anio, mes, hoy.getDate());
    cargarMes();
    puente.pregunta((json) => mostrarPregunta(json));
    puente.pregunta_cambio.connect(mostrarPregunta);
  });
} catch (error) {
  console.log("No se pudo conectar con Python: " + error);
}

// --- El mes -------------------------------------------------------------------------
function cargarMes(bajar = false) {
  puente.mes(anio, mes, (json) => dibujarMes(JSON.parse(json)));
  cargarDia(bajar);
}

function dibujarMes(m) {
  $("titulo-mes").textContent = m.titulo;
  const primero = (new Date(anio, mes - 1, 1).getDay() + 6) % 7;    // 0 = lunes
  const dias = new Date(anio, mes, 0).getDate();
  let html = "<div></div>".repeat(primero);
  for (let d = 1; d <= dias; d++) {
    const f = iso(anio, mes, d);
    const puntos = (m.puntos[f] || []).map((c) => `<i style="background:${c}"></i>`).join("");
    const clases = ["dia", f === m.hoy ? "hoy" : "", f === elegido ? "elegido" : ""].join(" ");
    html += `<div class="${clases}" data-fecha="${f}">${d}<span class="puntos">${puntos}</span></div>`;
  }
  $("grilla").innerHTML = html;
  $("grilla").querySelectorAll(".dia").forEach((el) => {
    el.onclick = () => { elegido = el.dataset.fecha; cargarMes(true); };
  });
}

function cargarDia(bajar = false) {
  puente.dia(elegido, (json) => {
    const d = JSON.parse(json);
    $("nombre-dia").textContent = d.nombre;
    $("lista-dia").innerHTML = d.eventos.length ? d.eventos.map((e) => `
      <div class="evento" data-id="${e.id}">
        <i style="background:${e.color}"></i><b>${escapar(e.titulo)}</b>
        <small>${e.repite ? "↻ " : ""}${e.hora || "Todo el día"}</small>
      </div>`).join("") : '<p class="vacio">Nada anotado</p>';
    $("lista-dia").querySelectorAll(".evento").forEach((el) => {
      el.onclick = () => abrirForm(Number(el.dataset.id));
    });
    if (bajar) $("lista-dia").scrollIntoView({ behavior: "smooth", block: "end" });
  });
}

function cambiarMes(paso) {
  mes += paso;
  if (mes < 1) { mes = 12; anio--; }
  if (mes > 12) { mes = 1; anio++; }
  elegido = iso(anio, mes, 1);
  cargarMes();
}

// --- El formulario -------------------------------------------------------------------
// --- ¿Se hizo? -----------------------------------------------------------------------
function mostrarPregunta(json) {
  pregunta = json ? JSON.parse(json) : null;
  $("pregunta").hidden = !pregunta;
  if (!pregunta) return;
  $("p-color").style.background = pregunta.color;
  $("p-texto").textContent = `¿Hiciste: ${pregunta.titulo}?`;
}

function responder(respuesta) {
  if (!pregunta) return;
  const p = pregunta;
  puente.responder(respuesta);
  if (respuesta !== "reprogramar") return;
  if (p.repite) {
    // Se repite: no tocamos la serie, creamos uno nuevo solo para esta vez
    puente.evento(p.id, (json) => {
      const e = JSON.parse(json);
      abrirForm(null, { titulo: e.titulo, fecha: p.dia, hora: e.hora,
                        aviso_min: e.aviso_min, repetir: "no", color: e.color });
    });
  } else {
    abrirForm(p.id);
  }
}

// --- El formulario -------------------------------------------------------------------
function mostrar(vista) {
  $("vista-mes").hidden = vista !== "mes";
  $("vista-form").hidden = vista !== "form";
}

function abrirForm(id, base = null) {
  editando = id;
  const cargar = (e) => {
    form = { titulo: e.titulo, fecha: e.fecha, hora: e.hora, aviso_min: e.aviso_min, repetir: e.repetir, color: e.color };
    $("titulo-form").textContent = id ? "Editar evento" : "Nuevo evento";
    $("btn-borrar").hidden = !id;
    $("f-titulo").value = form.titulo;
    $("f-fecha").value = form.fecha;
    $("f-hora").value = form.hora;
    $("f-todo-dia").checked = !form.hora;
    $("f-hora").disabled = !form.hora;
    dibujarOpciones();
    mostrar("form");
    $("f-titulo").focus();
  };
  if (base) cargar(base);
  else if (id) puente.evento(id, (json) => cargar(JSON.parse(json)));
  else cargar({ titulo: "", fecha: elegido, hora: "10:00", aviso_min: 10, repetir: "no", color: COLORES[0] });
}

function dibujarOpciones() {
  const grupo = (id, lista, clave) => {
    $(id).innerHTML = lista.map(([v, t]) => `<button class="tecla ${form[clave] === v ? "activa" : ""}" data-v="${v}">${t}</button>`).join("");
    $(id).querySelectorAll("button").forEach((b) => {
      b.onclick = () => { form[clave] = clave === "aviso_min" ? Number(b.dataset.v) : b.dataset.v; dibujarOpciones(); };
    });
  };
  grupo("f-aviso", AVISOS, "aviso_min");
  grupo("f-repetir", REPETIR, "repetir");
  $("f-color").innerHTML = COLORES.map((c) => `<button class="${form.color === c ? "elegido" : ""}" data-c="${c}" style="background:${c}"></button>`).join("");
  $("f-color").querySelectorAll("button").forEach((b) => { b.onclick = () => { form.color = b.dataset.c; dibujarOpciones(); }; });
}

function guardar() {
  form.titulo = $("f-titulo").value.trim();
  if (!form.titulo) { $("f-titulo").focus(); return; }
  form.fecha = $("f-fecha").value || elegido;
  form.hora = $("f-todo-dia").checked ? "" : ($("f-hora").value || "10:00");
  puente.guardar(JSON.stringify({ id: editando, ...form }), () => {
    elegido = form.fecha;
    [anio, mes] = form.fecha.split("-").map(Number);
    mostrar("mes");
    cargarMes(true);
  });
}

function borrar() {
  if (!editando) return;
  puente.borrar(editando, () => { mostrar("mes"); cargarMes(); });
}

// --- Eventos -------------------------------------------------------------------
$("btn-anterior").onclick = () => cambiarMes(-1);
$("btn-siguiente").onclick = () => cambiarMes(1);
$("btn-nuevo").onclick = () => abrirForm(null);
$("btn-volver").onclick = () => mostrar("mes");
$("btn-guardar").onclick = guardar;
$("btn-borrar").onclick = borrar;
$("f-titulo").addEventListener("keydown", (e) => { if (e.key === "Enter") guardar(); });
$("f-todo-dia").onchange = () => { $("f-hora").disabled = $("f-todo-dia").checked; };
$("p-si").onclick = () => responder("si");
$("p-no").onclick = () => responder("no");
$("p-repro").onclick = () => responder("reprogramar");