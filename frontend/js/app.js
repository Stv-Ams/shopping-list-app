// ============================================================
//  Shopping List — Frontend (Full-Stack)
//  Reemplaza localStorage por llamadas fetch() a la API REST.
// ============================================================

const API = '';

const TABS = [
  { key: "costco", label: "Costco", icon: "🏬" },
  { key: "super",  label: "Super",  icon: "🛒" },
  { key: "varios", label: "Varios", icon: "📋" },
  { key: "other",  label: "Other",  icon: "📦" }
];
const PRIS  = ["Alta", "Media", "Baja"];
const PRI_C = { Alta: "#ef4444", Media: "#f59e0b", Baja: "#6b7280" };
const PRI_E = { Alta: "🔴",       Media: "🟡",       Baja: "⚪" };
const QTY   = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "Muchos"];

let state     = { catalog: { costco: [], super: [], varios: [], other: [] },
                  lists:   { costco: [], super: [], varios: [], other: [] } };
let tab       = "costco";
let varP      = "Media";
let editMode  = false;
let qtyOpen   = null;
let catFilter = "";
let isDark    = false;

// ------------------------------------------------------------
//  API helpers  (reemplazan load() y save() de localStorage)
// ------------------------------------------------------------
async function apiGet(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error("GET " + path + " failed");
  return r.json();
}
async function apiSend(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!r.ok) throw new Error(method + " " + path + " failed");
  return r.json();
}

async function fetchState() {
  try {
    state = await apiGet("/api/cart");
  } catch (e) {
    console.error("No se pudo conectar con el backend:", e);
  }
}

// ------------------------------------------------------------
//  Init / theme
// ------------------------------------------------------------
async function init() {
  try { isDark = localStorage.getItem("sl-theme") === "dark"; } catch {}
  applyTheme();
  await fetchState();
  render();
}

function applyTheme() {
  document.body.className = isDark ? "dark" : "light";
  document.querySelector(".theme-btn").textContent = isDark ? "☀️" : "🌙";
  try { localStorage.setItem("sl-theme", isDark ? "dark" : "light"); } catch {}
}
function toggleTheme() { isDark = !isDark; applyTheme(); render(); }

function hasCat() { return tab === "costco" || tab === "super"; }
function hasP()   { return tab === "varios"; }
function closeQty() { if (qtyOpen !== null) { qtyOpen = null; render(); } }

// ------------------------------------------------------------
//  Render
// ------------------------------------------------------------
function renderTabs() {
  const el = document.getElementById("tabs");
  el.innerHTML = TABS.map(t => {
    const c = state.lists[t.key].filter(i => !i.checked).length;
    return `<button class="tab ${tab === t.key ? "active" : ""}" onclick="switchTab('${t.key}')">
              <span class="icon">${t.icon}</span><span>${t.label}</span>
              ${c ? `<span class="badge">${c}</span>` : ""}
            </button>`;
  }).join("");
}

function switchTab(k) { tab = k; editMode = false; qtyOpen = null; catFilter = ""; render(); }

function render() {
  renderTabs();
  const el  = document.getElementById("content");
  const list = state.lists[tab] || [];
  const cat  = state.catalog[tab] || [];
  const filtered = catFilter ? cat.filter(i => i.toLowerCase().includes(catFilter.toLowerCase())) : cat;
  const sorted = hasP() ? [...list].sort((a, b) => PRIS.indexOf(a.priority) - PRIS.indexOf(b.priority)) : list;
  const unc = sorted.filter(i => !i.checked);
  const chk = sorted.filter(i => i.checked);
  let h = "";

  // Catalog
  if (hasCat() && !editMode) {
    h += `<div class="section-header"><span class="section-label">Productos frecuentes</span><button class="edit-btn" onclick="editMode=true;render()">✏️ Editar</button></div>`;
    if (cat.length > 12)
      h += `<input class="cat-search" placeholder="Buscar en catálogo..." value="${esc(catFilter)}" oninput="catFilter=this.value;render()" onclick="event.stopPropagation()">`;
    h += `<div class="chips">${filtered.map((it, i) => {
      const inL = list.some(l => l.name.toLowerCase() === it.toLowerCase() && !l.checked);
      return `<button class="chip ${inL ? "in-list" : ""}" onclick="${inL ? "" : "addCat(" + i + ")"}">${inL ? "✓ " : "+ "}${esc(it)}</button>`;
    }).join("")}</div><div style="margin-bottom:16px"></div>`;
  }

  // Edit catalog
  if (hasCat() && editMode) {
    h += `<div class="edit-box">
            <div class="section-header"><span class="section-label">Editar catálogo</span>
              <button class="edit-btn" onclick="editMode=false;render()">✓ Listo</button>
            </div>
            <div class="input-row" style="margin-bottom:10px">
              <input class="text-input" id="newcat" placeholder="Nuevo producto..." onkeydown="if(event.key==='Enter')addCatNew()" onclick="event.stopPropagation()">
              <button class="add-btn" onclick="addCatNew()">+</button>
            </div>
            <div class="edit-chips">${cat.map((it, i) => `<span class="edit-chip">${esc(it)}<button onclick="rmCat(${i})">×</button></span>`).join("")}</div>
          </div>`;
  }

  // Free input
  h += `<div class="input-row" ${hasP() ? 'style="margin-bottom:8px"' : ''}>
          <input class="text-input" id="freetxt" placeholder="Agregar producto..." onkeydown="if(event.key==='Enter')addFree()" onclick="event.stopPropagation()">
          <button class="add-btn" onclick="addFree()">+</button>
        </div>`;

  // Priority
  if (hasP()) {
    h += `<div class="priority-row">${PRIS.map(p =>
      `<button class="pri-btn" style="border:${varP === p ? `2px solid ${PRI_C[p]}` : "1px solid " + (isDark ? "#475569" : "#cbd5e1")};background:${varP === p ? PRI_C[p] + "15" : (isDark ? "#1e293b" : "#fff")};color:${PRI_C[p]}" onclick="varP='${p}';render()">${PRI_E[p]} ${p}</button>`
    ).join("")}</div>`;
  }

  // Empty
  if (!unc.length && !chk.length)
    h += `<div class="empty"><div class="big">🛒</div><p>Lista vacía — agrega productos</p></div>`;

  // Items (unchecked)
  unc.forEach(item => {
    const ri = list.indexOf(item);
    h += `<div class="item-row">
            <button class="check-btn" onclick="tog(${ri})"></button>
            <div class="item-name">${esc(item.name)}</div>
            ${hasP() && item.priority ? `<span style="font-size:11px;font-weight:600;color:${PRI_C[item.priority]}">${PRI_E[item.priority]}</span>` : ""}
            <div style="position:relative;flex-shrink:0" onclick="event.stopPropagation()">
              <button class="qty-btn" onclick="toggleQty(${ri})">${item.qty === "Muchos" ? "M" : item.qty}</button>
              ${qtyOpen === ri ? `<div class="qty-popup">${QTY.map(q => `<button class="qty-opt ${q === "Muchos" ? "wide" : ""} ${item.qty === q ? "sel" : ""}" onclick="setQ(${ri},'${q}')">${q}</button>`).join("")}</div>` : ""}
            </div>
            <button class="remove-btn" onclick="rm(${ri})">×</button>
          </div>`;
  });

  // Checked
  if (chk.length) {
    h += `<div class="checked-section"><div class="checked-label">COMPLETADOS (${chk.length})</div>`;
    chk.forEach(item => {
      const ri = list.indexOf(item);
      h += `<div class="checked-row">
              <button class="check-btn checked" onclick="tog(${ri})">✓</button>
              <span class="checked-name">${esc(item.name)}</span>
              <button class="remove-btn" onclick="rm(${ri})">×</button>
            </div>`;
    });
    h += `</div>`;
  }

  // Actions
  if (list.length) {
    h += `<div class="actions">
            ${chk.length ? `<button class="action-btn clear" onclick="clrChk()">Limpiar completados</button>` : ""}
            <button class="action-btn danger" onclick="clrAll()">Vaciar lista</button>
          </div>`;
  }

  el.innerHTML = h;
  setTimeout(() => { const searchInput = document.querySelector('.cat-search'); if (searchInput && catFilter) { searchInput.focus(); searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length); } }, 0);
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ------------------------------------------------------------
//  Mutations  →  cada una llama al backend y refresca
// ------------------------------------------------------------
async function addCat(i) {
  const cat = state.catalog[tab];
  if (!cat || !cat[i]) return;
  const n = cat[i];
  if (state.lists[tab].some(l => l.name.toLowerCase() === n.toLowerCase() && !l.checked)) return;
  await apiSend("POST", "/api/add", { tab, name: n, qty: 1, priority: null });
  await fetchState(); render();
}

async function addFree() {
  const el = document.getElementById("freetxt");
  if (!el || !el.value.trim()) return;
  const n = el.value.trim();
  if (state.lists[tab].some(l => l.name.toLowerCase() === n.toLowerCase() && !l.checked)) return;
  await apiSend("POST", "/api/add", { tab, name: n, qty: 1, priority: hasP() ? varP : null });
  await fetchState(); render();
}

async function addCatNew() {
  const el = document.getElementById("newcat");
  if (!el || !el.value.trim()) return;
  await apiSend("POST", "/api/catalog/add", { tab, name: el.value.trim() });
  await fetchState(); render();
}

async function rmCat(i) {
  const name = state.catalog[tab][i];
  await apiSend("DELETE", "/api/catalog/remove", { tab, name });
  await fetchState(); render();
}

async function tog(i) {
  const item = state.lists[tab][i];
  if (!item) return;
  await apiSend("PUT", "/api/item/" + item.id, { checked: !item.checked });
  await fetchState(); render();
}

async function rm(i) {
  const item = state.lists[tab][i];
  if (!item) return;
  await apiSend("DELETE", "/api/item/" + item.id, null);
  await fetchState(); render();
}

function toggleQty(i) { qtyOpen = qtyOpen === i ? null : i; render(); }

async function setQ(i, q) {
  const item = state.lists[tab][i];
  if (!item) return;
  const qty = isNaN(q) ? q : Number(q);
  qtyOpen = null;
  await apiSend("PUT", "/api/item/" + item.id, { qty });
  await fetchState(); render();
}

async function clrChk() {
  await apiSend("DELETE", "/api/cart/" + tab + "/checked", null);
  await fetchState(); render();
}

async function clrAll() {
  await apiSend("DELETE", "/api/cart/" + tab, null);
  await fetchState(); render();
}

// ------------------------------------------------------------
//  Bootstrap
// ------------------------------------------------------------
init();
