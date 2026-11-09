let puente = null;
const $ = (id) => document.getElementById(id);
const NOMBRES = { clic: "Clic", suave: "Suave", retro: "Retro", ninguno: "Sin sonido" };
const barras = (nivel, maximo) => Array.from({ length: maximo }, (_, i) => `<i class="${i < nivel ? "llena" : ""}"></i>`).join("");

// --- Las cartas de personajes ---------------------------------------------------------
let cartas = [];        // la lista que manda Python: id, nombre, titulo, consola, imagen
let indice = 0;         // la carta que se está mirando
let actual = null;      // el personaje elegido ahora
let cambiando = false;

function oscurecer(hex, factor) {
  const n = parseInt(hex.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => Math.round(v * factor));
  return `rgb(${c.join(",")})`;
}

function mostrarCarta() {
  if (!cartas.length) return;
  const p = cartas[indice];
  dibujarQuieto(p);
  $("carta-nombre").textContent = p.nombre;
  $("carta-titulo").textContent = p.titulo;
  $("color-1").style.background = p.consola;
  $("color-2").style.background = p.detalle || oscurecer(p.consola, 0.6);
  $("puntos").innerHTML = cartas.map((_, i) => `<i class="${i === indice ? "on" : ""}"></i>`).join("");

  const boton = $("btn-elegir");
  const esActual = p.id === actual;
  boton.disabled = esActual || cambiando;
  boton.textContent = cambiando ? "Cambiando…" : esActual ? "Personaje actual" : "Elegir";
  boton.style.background = esActual ? "" : p.consola;
}

function mover(paso) {
  if (cambiando || !cartas.length) return;
  indice = (indice + paso + cartas.length) % cartas.length;
  puente.sonar("carta");
  mostrarCarta();
}

// --- Dibujar el estado que manda Python -----------------------------------------------
function dibujar(e) {
  $("barras-teclas").innerHTML = barras(e.teclas, e.maximo);
  $("barras-avisos").innerHTML = barras(e.avisos, e.maximo);
  $("tipos").innerHTML = e.tipos.map((t) =>
    `<button class="tecla ${t === e.tipo ? "activa" : ""}" data-tipo="${t}">${NOMBRES[t] || t}</button>`).join("");
  $("tipos").querySelectorAll("[data-tipo]").forEach((b) => {
    b.onclick = () => puente.tipo_tecla(b.dataset.tipo);
  });
  if (actual === null) actual = e.personaje;
  if (document.activeElement !== $("nombre")) $("nombre").value = e.nombre || "";
  $("version").textContent = `Quipu ${e.version}` + (e.nueva ? ` · hay una nueva: ${e.nueva}` : " · al día");
  const b = $("btn-actualizar");
  b.style.display = e.nueva ? "" : "none";
  if (e.descargando) { b.disabled = true; b.textContent = "Descargando…"; }
  else if (b.disabled) { b.disabled = false; b.textContent = "Actualizar"; }
}

// --- El ritual al elegir: escaneo, captura y lluvia de código -------------------------
const lienzo = $("carta-lienzo");
const cx = lienzo.getContext("2d");
const LW = 200, LH = 150, RES = 2;          // tamaño en pantalla y resolución interna (x2)
lienzo.width = LW * RES;
lienzo.height = LH * RES;
cx.scale(RES, RES);
const imagenes = {};                         // id del personaje -> imagen ya cargada
const SIGNOS = "01QUIPU{}<>/#=+*";

function cargarImagen(p) {
  if (!imagenes[p.id]) {
    const im = new Image();
    im.src = p.imagen;
    imagenes[p.id] = im;
  }
  return imagenes[p.id];
}

function caja(im) {                          // dónde va la imagen: centrada, casi todo el alto
  const h = LH - 6, w = im.width * h / im.height;
  return { x: (LW - w) / 2, y: 3, w, h };
}

function dibujarQuieto(p) {
  const im = cargarImagen(p);
  const pintar = () => {
    cx.clearRect(0, 0, LW, LH);
    const b = caja(im);
    cx.drawImage(im, b.x, b.y, b.w, b.h);
  };
  if (im.complete) pintar(); else im.onload = pintar;
}

function oscuro() {
  cx.fillStyle = "#14171D";
  cx.fillRect(0, 0, LW, LH);
}

function grilla() {
  cx.strokeStyle = "rgba(91,192,240,.12)";
  cx.lineWidth = 0.5;
  for (let x = 0; x <= LW; x += 8) { cx.beginPath(); cx.moveTo(x, 0); cx.lineTo(x, LH); cx.stroke(); }
  for (let y = 0; y <= LH; y += 8) { cx.beginPath(); cx.moveTo(0, y); cx.lineTo(LW, y); cx.stroke(); }
}

function silueta(im, b, color) {             // la figura pintada de un solo color
  const c = document.createElement("canvas");
  c.width = LW * RES;
  c.height = LH * RES;
  const g = c.getContext("2d");
  g.drawImage(im, b.x * RES, b.y * RES, b.w * RES, b.h * RES);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  return c;
}

function animar(duracion, cuadro, fin) {
  let t0 = null;
  function paso(ts) {
    if (t0 === null) t0 = ts;
    const t = ts - t0;
    cuadro(t, Math.min(1, t / duracion));
    if (t < duracion) requestAnimationFrame(paso); else fin();
  }
  requestAnimationFrame(paso);
}

function lluvia(p, im, b, fin) {
  // Imagen en baja resolución: los "píxeles" que se van uniendo justo detrás del código
  const baja = document.createElement("canvas");
  baja.width = Math.max(1, Math.round(b.w / 5));
  baja.height = Math.max(1, Math.round(b.h / 5));
  baja.getContext("2d").drawImage(im, 0, 0, baja.width, baja.height);

  const ancho = 4, zona = 22, velocidad = 0.12;        // ancho de columna, franja pixelada, px por ms
  const columnas = Array.from({ length: Math.ceil(LW / ancho) }, () => ({
    inicio: Math.random() * 900,
    signos: Array.from({ length: 7 }, () => SIGNOS[Math.floor(Math.random() * SIGNOS.length)]),
  }));
  const duracion = 900 + (LH + zona + 70) / velocidad;
  const [r, g, bl] = [1, 3, 5].map((i) => parseInt(p.consola.substr(i, 2), 16));

  animar(duracion, (t) => {
    oscuro();
    columnas.forEach((col, i) => {
      const cabeza = (t - col.inicio) * velocidad;
      if (cabeza <= 0) return;
      const x = i * ancho;
      const nitida = Math.max(0, Math.min(LH, cabeza - zona));
      if (nitida > 0) {                                  // ya revelada: la imagen real, nítida
        cx.save(); cx.beginPath(); cx.rect(x, 0, ancho, nitida); cx.clip();
        cx.imageSmoothingEnabled = true;
        cx.drawImage(im, b.x, b.y, b.w, b.h);
        cx.restore();
      }
      const fin2 = Math.max(0, Math.min(LH, cabeza));
      if (fin2 > nitida) {                               // franja de píxeles que se están uniendo
        cx.save(); cx.beginPath(); cx.rect(x, nitida, ancho, fin2 - nitida); cx.clip();
        cx.imageSmoothingEnabled = false;
        cx.drawImage(baja, b.x, b.y, b.w, b.h);
        cx.restore();
      }
      cx.font = "bold 6px monospace";
      cx.textAlign = "center";
      col.signos.forEach((s, j) => {                     // la cascada de código
        const y = cabeza - j * 7;
        if (y < -6 || y > LH + 6) return;
        if (Math.random() < 0.08) col.signos[j] = SIGNOS[Math.floor(Math.random() * SIGNOS.length)];
        cx.fillStyle = j === 0 ? "rgba(255,255,255,.95)" : `rgba(${r},${g},${bl},${0.9 - j * 0.12})`;
        cx.fillText(col.signos[j], x + ancho / 2, y);
      });
    });
  }, fin);
}

function ritual(p, alTerminar) {
  const im = cargarImagen(p);
  const b = caja(im);
  const sombra = silueta(im, b, "#2A3140");
  const celeste = silueta(im, b, "#5BC0F0");

  // 1. Escaneo: la silueta oscura y el haz que sube y baja tres veces
  puente.ritual("escaneo");
  animar(2600, (t, u) => {
    oscuro(); grilla();
    cx.drawImage(sombra, 0, 0, LW, LH);
    const haz = b.y + b.h * (0.5 - 0.5 * Math.cos(u * Math.PI * 3));
    cx.save(); cx.globalAlpha = 0.55;
    cx.beginPath(); cx.rect(0, b.y, LW, Math.max(0, haz - b.y)); cx.clip();
    cx.drawImage(celeste, 0, 0, LW, LH);
    cx.restore();
    cx.fillStyle = "rgba(91,192,240,.18)"; cx.fillRect(0, haz - 8, LW, 16);
    cx.fillStyle = "#BDE8FA"; cx.fillRect(0, haz - 1, LW, 2);
    cx.fillStyle = "#5BC0F0"; cx.font = "bold 9px monospace"; cx.textAlign = "left";
    cx.fillText(Math.round(u * 100) + "%", 6, LH - 6);
  }, () => {
    // 2. Captura: destello y la silueta que late una vez
    puente.ritual("captura");
    animar(900, (t) => {
      oscuro(); grilla();
      cx.drawImage(celeste, 0, 0, LW, LH);
      const s = 1 + 0.06 * Math.sin(t / 60);
      cx.save(); cx.globalAlpha = Math.max(0, 1 - t / 500);
      cx.drawImage(celeste, LW * (1 - s) / 2, LH * (1 - s) / 2, LW * s, LH * s);
      cx.restore();
      cx.fillStyle = `rgba(255,255,255,${Math.max(0, 0.85 - t / 300)})`;
      cx.fillRect(0, 0, LW, LH);
    }, () => {
      // 3. Creación: la lluvia de código forma la imagen real
      puente.ritual("creando");
      lluvia(p, im, b, () => {
        dibujarQuieto(p);
        puente.ritual("listo");
        alTerminar();
      });
    });
  });
}

// --- Conexión con Python --------------------------------------------------------------
try {
  new QWebChannel(qt.webChannelTransport, (canal) => {
    puente = canal.objects.puente;
    puente.cambio.connect((json) => dibujar(JSON.parse(json)));
    puente.estado((json) => {
      dibujar(JSON.parse(json));
      puente.personajes((lista) => {
        cartas = JSON.parse(lista);
        indice = Math.max(0, cartas.findIndex((p) => p.id === actual));
        mostrarCarta();
      });
    });
  });
} catch (error) {
  console.log("No se pudo conectar con Python: " + error);
}

// --- Botones fijos ----------------------------------------------------------------------
$("anterior").onclick = () => mover(-1);
$("siguiente").onclick = () => mover(1);
$("btn-elegir").onclick = () => {
  const p = cartas[indice];
  if (!p || p.id === actual || cambiando) return;
 cambiando = true;
  mostrarCarta();
  puente.sonar("tecla");
  ritual(p, () => setTimeout(() => puente.elegir(p.id), 1200));   // al terminar, se guarda y reinicia   // al terminar, se guarda y reinicia
};

document.querySelectorAll(".mm").forEach((b) => {
  b.onclick = () => puente.volumen(b.dataset.clave, Number(b.dataset.paso));
});
$("btn-carpeta").onclick = () => puente.abrir_carpeta();

// Salir pide un segundo toque, para no cerrar Quipu sin querer
let confirmarHasta = 0;
$("btn-salir").onclick = () => {
  const boton = $("btn-salir");
  if (Date.now() < confirmarHasta) {
    boton.disabled = true;
    puente.salir();
    return;
  }
  confirmarHasta = Date.now() + 3000;
  boton.classList.add("confirmar");
  boton.textContent = "¿Seguro? Tocá de nuevo";
  setTimeout(() => {
    if (!boton.disabled) { boton.classList.remove("confirmar"); boton.textContent = "Salir de Quipu"; }
  }, 3000);
};

// Tu nombre: se guarda con el botón o con Enter
function guardarNombre() {
  const nombre = $("nombre").value.trim();
  if (nombre) { puente.guardar_nombre(nombre); $("nombre").blur(); }
}
$("btn-nombre").onclick = guardarNombre;
$("nombre").addEventListener("keydown", (ev) => { if (ev.key === "Enter") guardarNombre(); });

// Actualizar pide un segundo toque, para no cerrar Quipu sin querer
let confirmarActualizar = 0;
$("btn-actualizar").onclick = () => {
  const b = $("btn-actualizar");
  if (Date.now() < confirmarActualizar) {
    b.disabled = true;
    b.textContent = "Descargando…";
    puente.actualizar();
    return;
  }
  confirmarActualizar = Date.now() + 3000;
  b.textContent = "¿Actualizar? Tocá de nuevo";
  setTimeout(() => { if (!b.disabled) b.textContent = "Actualizar"; }, 3000);
};