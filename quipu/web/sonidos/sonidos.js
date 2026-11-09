let puente = null;
const $ = (id) => document.getElementById(id);

// --- Íconos de cada sonido ----------------------------------------------------------
const ICONOS = {
  lluvia: '<path d="M9 22h22a6 6 0 0 0 0-12 9 9 0 0 0-17-1 6.5 6.5 0 0 0-5 13z" fill="#DDE6EE" stroke="#5E7B92" stroke-width="2"/><g stroke="#3FA9F5" stroke-width="3" stroke-linecap="round"><path d="M13 27l-2 6M21 27l-2 6M29 27l-2 6"/></g>',
  rio: '<g fill="none" stroke="#2F80ED" stroke-width="3" stroke-linecap="round"><path d="M4 14q6-5 12 0t12 0 8-2"/><path d="M4 22q6-5 12 0t12 0 8-2"/><path d="M4 30q6-5 12 0t12 0 8-2"/></g>',
  fogon: '<path d="M20 4c3 7 10 10 10 19a10 10 0 0 1-20 0c0-5 3-8 5-10 0 4 2 6 4 6-2-6 0-11 1-15z" fill="#F2994A" stroke="#B85A1A" stroke-width="2" stroke-linejoin="round"/><path d="M10 36h20" stroke="#7A4B2A" stroke-width="3" stroke-linecap="round"/>',
  viento: '<g fill="none" stroke="#5E7B92" stroke-width="3" stroke-linecap="round"><path d="M4 14h20a5 5 0 1 0-5-5"/><path d="M4 22h28a5 5 0 1 1-5 5"/><path d="M4 30h12"/></g>',
  campo: '<path d="M8 30q12-2 18-14l8-2-6 6q-4 10-20 10z" fill="#E5A23A" stroke="#8A5A1A" stroke-width="2" stroke-linejoin="round"/><circle cx="27" cy="18" r="1.6" fill="#2B2B33"/><path d="M4 36h32" stroke="#4E8F2E" stroke-width="3" stroke-linecap="round"/>',
};
const barras = (nivel, maximo) => Array.from({ length: maximo }, (_, i) => `<i class="${i < nivel ? "llena" : ""}"></i>`).join("");

// --- Dibujar el estado que manda Python -----------------------------------------------
function dibujar(e) {
  $("lista").innerHTML = e.sonidos.map((s) => `
    <div class="sonido ${s.on ? "on" : ""}" data-clave="${s.clave}">
      <svg viewBox="0 0 40 40">${ICONOS[s.clave] || ""}</svg>
      <b>${s.nombre}</b>
      <span class="estado">${s.on ? "ON" : "OFF"}</span>
      <div class="control">
        <button class="mm" data-paso="-1">−</button>
        <span class="barras">${barras(s.nivel, e.maximo)}</span>
        <button class="mm" data-paso="1">+</button>
      </div>
    </div>`).join("");

  $("lista").querySelectorAll(".sonido").forEach((fila) => {
    const clave = fila.dataset.clave;
    fila.onclick = () => puente.alternar(clave);              // tocar la fila: prender o apagar
    fila.querySelectorAll(".mm").forEach((b) => {
      b.onclick = (ev) => { ev.stopPropagation(); puente.nivel(clave, Number(b.dataset.paso)); };
    });
  });

  $("gen-barras").innerHTML = barras(e.general, e.maximo);
  document.querySelectorAll("[data-min]").forEach((b) => b.classList.remove("activa"));
  $("aviso-tempo").textContent = e.minutos !== null ? `Se apagan en ${e.minutos} min` : "";
}

// --- Conexión con Python --------------------------------------------------------------
try {
  new QWebChannel(qt.webChannelTransport, (canal) => {
    puente = canal.objects.puente;
    puente.cambio.connect((json) => dibujar(JSON.parse(json)));
    puente.estado((json) => dibujar(JSON.parse(json)));
  });
} catch (error) {
  console.log("No se pudo conectar con Python: " + error);
}

// --- Botones fijos ----------------------------------------------------------------------
$("btn-apagar").onclick = () => puente.apagar_todo();
$("gen-menos").onclick = () => puente.general(-1);
$("gen-mas").onclick = () => puente.general(1);
document.querySelectorAll("[data-min]").forEach((b) => {
  b.onclick = () => puente.temporizador(Number(b.dataset.min));
});