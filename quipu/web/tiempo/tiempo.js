// --- Estado -------------------------------------------------------------------
let puente = null;
let ajustes = null;      // los ajustes guardados
let borrador = null;     // los ajustes mientras los estás cambiando

const $ = (id) => document.getElementById(id);
const escapar = (t) => String(t ?? "").replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// --- Íconos del tiempo (dibujados, nítidos a cualquier tamaño) --------------------
const NUBE = '<path d="M12 34h22a7 7 0 0 0 0-14 10 10 0 0 0-19-1 7.5 7.5 0 0 0-3 15z" fill="#F4FBFD" stroke="#5E7B92" stroke-width="2"/>';
const ICONOS = {
  sol: '<circle cx="22" cy="22" r="9" fill="#F2C230" stroke="#B8862A" stroke-width="2"/><g stroke="#F2C230" stroke-width="3" stroke-linecap="round"><path d="M22 4v5M22 35v5M4 22h5M35 22h5M9 9l3.5 3.5M31.5 31.5L35 35M35 9l-3.5 3.5M9 35l3.5-3.5"/></g>',
  nube: '<circle cx="15" cy="15" r="8" fill="#F2C230"/>' + NUBE,
  lluvia: NUBE.replace('34h', '28h').replace('M12', 'M12').replace('#F4FBFD', '#DDE6EE') +
    '<g stroke="#3FA9F5" stroke-width="3" stroke-linecap="round"><path d="M15 33l-2 6M23 33l-2 6M31 33l-2 6"/></g>',
  tormenta: NUBE.replace('#F4FBFD', '#C9D3DC') + '<path d="M22 32l-4 7h5l-3 6" fill="none" stroke="#F2C230" stroke-width="3" stroke-linejoin="round"/>',
  nieve: NUBE + '<g fill="#7FB8E0"><circle cx="15" cy="39" r="2"/><circle cx="23" cy="41" r="2"/><circle cx="31" cy="39" r="2"/></g>',
  niebla: '<g stroke="#8AA5B8" stroke-width="3" stroke-linecap="round"><path d="M8 16h28M5 23h34M8 30h28"/></g>',
};
const icono = (nombre) => `<svg viewBox="0 0 44 44">${ICONOS[nombre] || ICONOS.nube}</svg>`;

// --- Conexión con Python --------------------------------------------------------
try {
  new QWebChannel(qt.webChannelTransport, (canal) => {
    puente = canal.objects.puente;
    puente.pronostico_listo.connect((json) => mostrarPronostico(JSON.parse(json)));
    puente.ajustes((json) => { ajustes = JSON.parse(json); pedirPronostico(); });
  });
} catch (error) {
  console.log("No se pudo conectar con Python: " + error);
}

// --- Pronóstico -------------------------------------------------------------------
function pedirPronostico() {
  $("ciudad").textContent = ajustes.ciudad;
  $("cargando").hidden = false;
  $("error").hidden = true;
  puente.pedir_pronostico();
}

function mostrarPronostico(p) {
  $("cargando").hidden = true;
  if (!p.ok) {
    $("error").hidden = false;
    $("texto-error").textContent = p.error;
    $("actual").hidden = true;
    $("dias").innerHTML = "";
    return;
  }
  $("ciudad").textContent = p.ciudad;
  $("actual").hidden = false;
  $("icono-actual").innerHTML = icono(p.actual.icono);
  $("temp-actual").textContent = `${p.actual.temp}°${p.unidad}`;
  $("desc-actual").textContent = `${p.actual.descripcion} · viento ${p.actual.viento} km/h`;
  $("dias").innerHTML = p.dias.map((d) => `
    <div class="dia">
      <b>${d.nombre}</b>${icono(d.icono)}
      <span class="d">${escapar(d.descripcion)}</span>
      <span class="lluvia">${d.lluvia ? d.lluvia + "%" : ""}</span>
      <span class="mm">${d.max}° <i>${d.min}°</i></span>
    </div>`).join("");
}

// --- Ajustes -----------------------------------------------------------------------
function abrirAjustes() {
  borrador = { ...ajustes };
  $("buscar").value = "";
  $("resultados").hidden = true;
  dibujarAjustes();
  $("pronostico").hidden = true;
  $("ajustes").hidden = false;
}

function dibujarAjustes() {
  $("elegida").innerHTML = `📍 ${escapar(borrador.ciudad)} <small>${escapar(borrador.provincia)}, ${escapar(borrador.pais)}</small>`;
  document.querySelectorAll("[data-unidad]").forEach((b) => b.classList.toggle("activa", b.dataset.unidad === borrador.unidad));
  document.querySelectorAll("[data-dias]").forEach((b) => b.classList.toggle("activa", Number(b.dataset.dias) === borrador.dias));
}

function buscarCiudad() {
  const nombre = $("buscar").value.trim();
  if (nombre.length < 2) return;
  const lista = $("resultados");
  lista.hidden = false;
  lista.innerHTML = "<small>Buscando…</small>";
  puente.buscar(nombre, (json) => {
    const r = JSON.parse(json);
    if (!r.ok) { lista.innerHTML = `<small>${escapar(r.error)}</small>`; return; }
    if (!r.ciudades.length) { lista.innerHTML = "<small>No encontré esa ciudad.</small>"; return; }
    lista.innerHTML = r.ciudades.map((c, i) =>
      `<button data-i="${i}">${escapar(c.ciudad)} <small>${escapar(c.provincia)}, ${escapar(c.pais)}</small></button>`).join("");
    lista.querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        Object.assign(borrador, r.ciudades[Number(b.dataset.i)]);
        lista.hidden = true;
        $("buscar").value = "";
        dibujarAjustes();
      };
    });
  });
}

function guardarAjustes() {
  ajustes = { ...borrador };
  puente.guardar(JSON.stringify(ajustes));
  $("ajustes").hidden = true;
  $("pronostico").hidden = false;
  $("ciudad").textContent = ajustes.ciudad;
  $("cargando").hidden = false;
}

// --- Eventos -------------------------------------------------------------------
$("btn-ajustes").onclick = abrirAjustes;
$("btn-volver").onclick = () => { $("ajustes").hidden = true; $("pronostico").hidden = false; };
$("btn-buscar").onclick = buscarCiudad;
$("buscar").addEventListener("keydown", (e) => { if (e.key === "Enter") buscarCiudad(); });
$("btn-guardar").onclick = guardarAjustes;
$("btn-reintentar").onclick = pedirPronostico;
document.querySelectorAll("[data-unidad]").forEach((b) => { b.onclick = () => { borrador.unidad = b.dataset.unidad; dibujarAjustes(); }; });
document.querySelectorAll("[data-dias]").forEach((b) => { b.onclick = () => { borrador.dias = Number(b.dataset.dias); dibujarAjustes(); }; });