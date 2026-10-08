/* ============================================================
   MAQUIRENT - LÓGICA DE LA APLICACIÓN FRONTEND
   Conecta con el backend Django REST Framework mediante fetch()
   ============================================================ */

// La página se sirve desde Django para que la API use el mismo origen y no falle por CORS.
const API_BASE = window.location.origin;

// El API es la fuente de inventario e imagen; esta imagen solo cubre equipos sin foto.
const FALLBACK_MACHINE_IMAGE = 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=900&auto=format&fit=crop&q=82';
const MACHINE_CATALOG = [];

// ===== ESTADO GLOBAL =====
let currentFilter = 'all';
let currentSearch = '';
let cart = [];
let authToken = localStorage.getItem('maquirent_access_token');
let refreshToken = localStorage.getItem('maquirent_refresh_token');
let selectedMachine = null;
let lastModalTrigger = null;

// ===== UTILIDADES =====
const fmt = (n) => `$${Number(n).toLocaleString('es-CL')}`;
const localISODate = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const isLocalFile = () => window.location.protocol === 'file:';
function requireConnectedSite() {
  if (!isLocalFile()) return false;
  document.getElementById('localModeNote').hidden = false;
  showToast('Abre el sitio conectado desde el aviso superior para usar tu cuenta.', 'error');
  return true;
}
// Lee los claims del JWT para separar las pantallas de cliente y ejecutivo.
function readTokenClaims() {
  try {
    const encoded = authToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(encoded);
    const payload = Uint8Array.from(binary, character => character.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(payload));
  } catch { return {}; }
}
const isExecutiveSession = () => {
  const claims = readTokenClaims();
  return claims.rol === 'ADMIN' || claims.is_superuser === true;
};
function updateAccountInterface() {
  const executive = Boolean(authToken) && isExecutiveSession();
  document.getElementById('loginBtn').textContent = authToken ? 'Cerrar sesión' : 'Iniciar sesión';
  document.getElementById('adminNavItem').hidden = !executive;
  document.getElementById('adminPanel').hidden = !executive;
  document.getElementById('cartBtn').hidden = executive;
  document.getElementById('registerBtn').style.display = authToken ? 'none' : '';
  if (!executive) {
    document.getElementById('adminOrders').innerHTML = '';
    document.getElementById('adminMachineList').innerHTML = '';
    document.getElementById('adminStats').innerHTML = '';
    document.getElementById('adminOrderCount').textContent = '0';
  }
  renderCatalog(currentFilter);
}
// El catálogo procede de la base de datos; escapar texto antes de insertarlo como HTML evita XSS.
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

// Renueva silenciosamente el JWT vencido para que la persistencia del carro no termine al cabo de una hora.
async function apiFetch(url, options = {}) {
  const send = () => fetch(url, { ...options, headers: { ...(options.headers || {}), Authorization: `Bearer ${authToken}` } });
  let response = await send();
  if (response.status !== 401 || !refreshToken) return response;
  const refreshed = await fetch(`${API_BASE}/api/token/refresh/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh: refreshToken })
  });
  if (!refreshed.ok) {
    authToken = null; refreshToken = null;
    localStorage.removeItem('maquirent_access_token'); localStorage.removeItem('maquirent_refresh_token');
    localStorage.removeItem('maquirent_username');
    cart = [];
    updateAccountInterface();
    updateCartBadge();
    throw new Error('La sesión venció. Inicia sesión otra vez.');
  }
  const tokens = await refreshed.json();
  authToken = tokens.access;
  localStorage.setItem('maquirent_access_token', authToken);
  return send();
}

function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  setTimeout(() => { toast.classList.remove('show'); }, 3000);
}

function openModal(id) {
  lastModalTrigger = document.activeElement;
  document.getElementById(id).classList.add('active');
  document.body.classList.add('modal-open');
  const firstField = document.getElementById(id).querySelector('input') || document.getElementById(id).querySelector('button');
  firstField?.focus();
}
function closeModal(id) {
  document.getElementById(id).classList.remove('active');
  if (!document.querySelector('.modal-overlay.active')) document.body.classList.remove('modal-open');
  lastModalTrigger?.focus?.();
}

// ===== NAVBAR SCROLL =====
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  nav.classList.toggle('scrolled', window.scrollY > 30);
});

// ===== RENDERIZAR CATÁLOGO =====
function renderCatalog(filter = 'all') {
  const grid = document.getElementById('catalogGrid');
  const needle = currentSearch.trim().toLocaleLowerCase('es-CL');
  const minPrice = Number(document.getElementById('priceMin').value) || 0;
  const maxValue = document.getElementById('priceMax').value;
  const maxPrice = maxValue === '' ? Number.POSITIVE_INFINITY : Number(maxValue);
  const filtered = MACHINE_CATALOG.filter(machine =>
    (filter === 'all' || machine.categoria === filter) &&
    Number(machine.tarifa_diaria) >= minPrice && Number(machine.tarifa_diaria) <= maxPrice &&
    (!needle || `${machine.nombre} ${machine.categoria}`.toLocaleLowerCase('es-CL').includes(needle))
  );
  document.getElementById('catalogCount').textContent = `${filtered.length} ${filtered.length === 1 ? 'equipo' : 'equipos'}`;
  if (!filtered.length) {
    grid.innerHTML = '<p class="catalog-message">No hay maquinaria disponible en esta categoría por ahora.</p>';
    return;
  }

  grid.innerHTML = filtered.map(machine => {
    const stockOk = machine.stock_disponible > 0;
    return `
      <div class="machine-card" data-cat="${escapeHtml(machine.categoria)}">
        <div class="card-img-wrapper">
          <img src="${machine.img}" alt="${escapeHtml(machine.nombre)}" loading="lazy" />
          <span class="card-badge">${escapeHtml(machine.categoria)}</span>
          <span class="card-stock ${stockOk ? 'stock-ok' : 'stock-out'}">
            ${stockOk ? `${machine.stock_disponible} disponibles` : 'Sin stock'}
          </span>
        </div>
        <div class="card-body">
          <h3 class="card-title">${escapeHtml(machine.nombre)}</h3>
          <div class="card-price-row"><p class="card-tarifa">${fmt(machine.tarifa_diaria)} <span>/ día</span></p><p class="card-garantia">Garantía<br>${fmt(machine.garantia_fija)}</p></div>
          <button class="card-add-btn" 
            onclick="handleAddClick(${machine.id})"
            ${!stockOk ? 'disabled' : ''} ${isExecutiveSession() ? 'hidden' : ''}>
            ${stockOk ? '+ Agregar al Carro' : 'Sin Disponibilidad'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Construye categorías desde el API, así no desaparecen categorías agregadas por administración.
function renderFilters() {
  const categories = ['all', ...new Set(MACHINE_CATALOG.map(machine => machine.categoria).filter(Boolean))];
  const bar = document.getElementById('filterBar');
  if (currentFilter !== 'all' && !categories.includes(currentFilter)) currentFilter = 'all';
  bar.innerHTML = categories.map(category => {
    const label = category === 'all' ? 'Todos los equipos' : escapeHtml(category);
    return `<button class="filter-btn ${currentFilter === category ? 'active' : ''}" type="button" data-filter="${escapeHtml(category)}" aria-pressed="${currentFilter === category}">${label}</button>`;
  }).join('');
}
document.getElementById('filterBar').addEventListener('click', (event) => {
  const button = event.target.closest('[data-filter]');
  if (!button) return;
  currentFilter = button.dataset.filter;
  renderFilters();
  renderCatalog(currentFilter);
});
document.getElementById('catalogSearch').addEventListener('input', (event) => {
  currentSearch = event.target.value;
  renderCatalog(currentFilter);
});
// Mantiene el rango de precio aplicado mientras cambia el inventario visible.
['priceMin', 'priceMax'].forEach(id => {
  document.getElementById(id).addEventListener('input', () => renderCatalog(currentFilter));
});

// ===== CLIC EN "AGREGAR AL CARRO" =====
function handleAddClick(machineId) {
  if (requireConnectedSite()) return;
  if (!authToken) {
    showToast('Debes iniciar sesión para arrendar.', 'error');
    openModal('loginModal');
    return;
  }
  selectedMachine = MACHINE_CATALOG.find(m => m.id === machineId);
  if (!selectedMachine || selectedMachine.stock_disponible < 1) {
    showToast('Esta maquinaria no tiene unidades disponibles.', 'error');
    return;
  }
  document.getElementById('addCartTitle').textContent = `Arrendar: ${selectedMachine.nombre}`;
  document.getElementById('addCartDesc').textContent = `${fmt(selectedMachine.tarifa_diaria)}/día + ${fmt(selectedMachine.garantia_fija)} de garantía`;
  document.getElementById('addCartError').textContent = '';
  document.getElementById('costPreview').style.display = 'none';
  document.getElementById('addCartForm').reset();
  document.getElementById('fechaInicio').min = localISODate();
  document.getElementById('fechaFin').min = localISODate();
  openModal('addCartModal');
}

// ===== CALCULAR COSTO EN TIEMPO REAL =====
function calcCost() {
  if (!selectedMachine) return;
  document.getElementById('costPreview').style.display = 'none';
  const inicio = document.getElementById('fechaInicio').value;
  const fin = document.getElementById('fechaFin').value;
  if (!inicio || !fin) return;
  const dias = Math.ceil((new Date(fin) - new Date(inicio)) / 86400000);
  if (dias <= 0) return;
  const costo = selectedMachine.tarifa_diaria * dias + selectedMachine.garantia_fija;
  document.getElementById('costValue').textContent = `${fmt(costo)} (${dias} días)`;
  document.getElementById('costPreview').style.display = 'flex';
}
document.getElementById('fechaInicio').addEventListener('change', calcCost);
document.getElementById('fechaFin').addEventListener('change', calcCost);
document.getElementById('fechaInicio').addEventListener('change', (event) => {
  document.getElementById('fechaFin').min = event.target.value || localISODate();
});

// ===== FORMULARIO AGREGAR AL CARRO =====
document.getElementById('addCartForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const inicio = document.getElementById('fechaInicio').value;
  const fin = document.getElementById('fechaFin').value;
  const errEl = document.getElementById('addCartError');
  errEl.textContent = '';

  if (new Date(inicio) >= new Date(fin)) {
    errEl.textContent = 'La fecha de inicio debe ser anterior a la de fin.';
    return;
  }

  if (!authToken) {
    errEl.textContent = 'Inicia sesión para guardar tu carro.';
    return;
  }
  const submitButton = e.currentTarget.querySelector('[type="submit"]');
  if (submitButton.disabled) return;
  submitButton.disabled = true;
  // El carro persistente solo se confirma cuando responde la API; no se simula éxito.
  try {
    const res = await apiFetch(`${API_BASE}/api/carro-arriendo/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ maquinaria: selectedMachine.id, fecha_inicio: inicio, fecha_fin: fin })
    });

    if (res.ok) {
      await fetchCartFromBackend();
      await fetchCatalog();
      closeModal('addCartModal');
      showToast(`${selectedMachine.nombre} agregado al carro.`);
      return;
    }
    const error = await res.json();
    errEl.textContent = errorText(error);
  } catch (err) {
    errEl.textContent = 'No se pudo guardar. Comprueba tu conexión e inténtalo otra vez.';
  } finally {
    submitButton.disabled = false;
  }
});

function errorText(error) {
  if (typeof error === 'string') return error;
  return Object.values(error || {}).flat(Infinity).join(' ') || 'No fue posible completar la operación.';
}

function updateCartBadge() {
  document.getElementById('cartBadge').textContent = cart.length;
}

// ===== RENDER CARRO =====
function renderCart() {
  const listEl = document.getElementById('cartItems');
  const totalEl = document.getElementById('cartTotal');

  if (cart.length === 0) {
    listEl.innerHTML = '<div class="cart-empty">Tu carro está vacío. Agrega un equipo y vuelve aquí cuando quieras.</div>';
    totalEl.textContent = '$0';
    document.getElementById('cartModalCount').textContent = '0 equipos';
    document.getElementById('checkoutBtn').disabled = true;
    return;
  }

  listEl.innerHTML = cart.map((item) => `
    <div class="cart-item">
      <div class="cart-item-info">
        <h4>${escapeHtml(item.machine.nombre)}</h4>
        <p>${item.inicio} → ${item.fin} · ${item.dias} días</p>
      </div>
      <span class="cart-item-price">${fmt(item.costo)}</span>
      <button class="cart-remove" type="button" aria-label="Quitar ${escapeHtml(item.machine.nombre)}" onclick="removeCartItem(${Number(item.id)})">Quitar</button>
    </div>
  `).join('');

  const total = cart.reduce((acc, i) => acc + Number(i.costo), 0);
  totalEl.textContent = fmt(total);
  document.getElementById('cartModalCount').textContent = `${cart.length} ${cart.length === 1 ? 'equipo' : 'equipos'}`;
  document.getElementById('checkoutBtn').disabled = false;
}

// ===== BOTÓN CARRO =====
document.getElementById('cartBtn').addEventListener('click', async () => {
  if (requireConnectedSite()) return;
  if (!authToken) { openModal('loginModal'); showToast('Inicia sesión para ver tu carro guardado.', 'error'); return; }
  await fetchCartFromBackend();
  renderCart();
  openModal('cartModal');
});

// ===== CHECKOUT =====
document.getElementById('checkoutBtn').addEventListener('click', async () => {
  if (requireConnectedSite()) return;
  if (!authToken) { showToast('Inicia sesión para confirmar el arriendo.', 'error'); return; }
  if (cart.length === 0) return;
  const button = document.getElementById('checkoutBtn');
  if (button.disabled) return;
  button.disabled = true;

  try {
    const res = await apiFetch(`${API_BASE}/api/contratos/checkout/`, {
      method: 'POST'
    });
    if (res.ok) {
      const contrato = await res.json();
      await fetchCartFromBackend();
      await fetchCatalog();
      updateCartBadge();
      closeModal('cartModal');
      showToast(`Contrato generado. Folio: ${contrato.codigo_uuid}. Estado: PENDIENTE.`);
      return;
    }
    const error = await res.json();
    showToast(errorText(error.error || error), 'error');
  } catch (err) { showToast('No se pudo confirmar. Tu carro sigue guardado.', 'error'); }
  finally { button.disabled = cart.length === 0; }
});

// Borrar requiere el ID persistido del ítem, no solo eliminarlo de la interfaz.
async function removeCartItem(itemId) {
  try {
    const res = await apiFetch(`${API_BASE}/api/carro-arriendo/${itemId}/`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) throw new Error('delete failed');
    await fetchCartFromBackend(); renderCart();
  } catch (err) { showToast('No se pudo quitar el equipo del carro.', 'error'); }
}
window.removeCartItem = removeCartItem;

// ===== LOGIN =====
document.getElementById('loginBtn').addEventListener('click', () => {
  if (requireConnectedSite()) return;
  if (authToken) {
    authToken = null; refreshToken = null; cart = [];
    localStorage.removeItem('maquirent_access_token'); localStorage.removeItem('maquirent_refresh_token'); localStorage.removeItem('maquirent_username');
    document.getElementById('loginBtn').textContent = 'Iniciar sesión';
      updateAccountInterface();
    updateCartBadge(); showToast('Sesión cerrada. Tu carro queda guardado en tu cuenta.');
    return;
  }
  openModal('loginModal');
});
document.getElementById('registerBtn').addEventListener('click', () => {
  if (requireConnectedSite()) return;
  document.getElementById('registerError').textContent = '';
  openModal('registerModal');
});

document.getElementById('goLogin').addEventListener('click', () => { closeModal('registerModal'); openModal('loginModal'); });
document.getElementById('loginGoRegister').addEventListener('click', () => { closeModal('loginModal'); openModal('registerModal'); });
document.getElementById('closeRegister').addEventListener('click', () => closeModal('registerModal'));
document.getElementById('togglePassword').addEventListener('click', (event) => {
  const field = document.getElementById('registerPassword');
  const visible = field.type === 'password';
  field.type = visible ? 'text' : 'password';
  event.currentTarget.textContent = visible ? 'Ocultar' : 'Mostrar';
  event.currentTarget.setAttribute('aria-pressed', String(visible));
  field.focus();
});
document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (requireConnectedSite()) return;
  const errorEl = document.getElementById('registerError'); errorEl.textContent = '';
  const button = e.currentTarget.querySelector('[type="submit"]');
  if (button.disabled) return;
  button.disabled = true;
  const payload = { username: document.getElementById('registerUser').value.trim(), email: document.getElementById('registerEmail').value.trim(), password: document.getElementById('registerPassword').value };
  try {
    const res = await fetch(`${API_BASE}/api/registro/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await res.json();
    if (!res.ok) { errorEl.textContent = errorText(data); return; }
    // Al crear la cuenta, inicia sesión con los mismos datos para evitar pedir la clave dos veces.
    let sessionResponse = null;
    let session = null;
    try {
      sessionResponse = await fetch(`${API_BASE}/api/token/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: payload.username, password: payload.password })
      });
      session = await sessionResponse.json();
    } catch (sessionError) { /* La cuenta ya se creó; ofrecer login manual si falla la sesión automática. */ }
    if (sessionResponse?.ok) {
      authToken = session.access; refreshToken = session.refresh;
      localStorage.setItem('maquirent_access_token', authToken);
      localStorage.setItem('maquirent_refresh_token', refreshToken);
      localStorage.setItem('maquirent_username', payload.username);
      closeModal('registerModal');
      document.getElementById('loginBtn').textContent = 'Cerrar sesión';
      updateAccountInterface();
      await fetchCartFromBackend();
      showToast('Cuenta creada. Ya puedes armar tu solicitud.');
    } else {
      closeModal('registerModal');
      document.getElementById('loginUser').value = payload.username;
      openModal('loginModal');
      showToast('Cuenta creada. Inicia sesión para continuar.');
    }
  } catch (err) { errorEl.textContent = 'No se pudo conectar con el servidor.'; }
  finally { button.disabled = false; }
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (requireConnectedSite()) return;
  const username = document.getElementById('loginUser').value;
  const password = document.getElementById('loginPass').value;
  const errEl = document.getElementById('loginError');
  errEl.textContent = '';
  const button = e.currentTarget.querySelector('[type="submit"]');
  if (button.disabled) return;
  button.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    if (res.ok) {
      authToken = data.access;
      refreshToken = data.refresh;
      localStorage.setItem('maquirent_access_token', authToken);
      localStorage.setItem('maquirent_refresh_token', refreshToken);
      localStorage.setItem('maquirent_username', username);
      closeModal('loginModal');
      document.getElementById('loginBtn').textContent = 'Cerrar sesión';
      updateAccountInterface();
      showToast(`Bienvenido, ${username}!`);

      if (isExecutiveSession()) await loadExecutiveDashboard();
      else await fetchCartFromBackend();
    } else {
      errEl.textContent = 'Usuario o contraseña incorrectos.';
    }
  } catch (err) {
    errEl.textContent = 'No se pudo conectar con el servidor. Verifica que esté activo.';
  } finally {
    button.disabled = false;
  }
});

// ===== CARGAR CARRO DESDE BACKEND =====
async function fetchCartFromBackend() {
  if (!authToken || isExecutiveSession() || isLocalFile()) return;
  try {
    // Espera al catálogo para que los artículos restaurados tengan su nombre y precio actuales.
    await fetchCatalog();
    const res = await apiFetch(`${API_BASE}/api/carro-arriendo/`);
    if (res.ok) {
      const data = await res.json();
      // Sincronizar items del backend con el estado local
      const items = data.items || (data[0] && data[0].items) || [];
      cart = items.map(item => ({
        id: item.id,
        machine: MACHINE_CATALOG.find(m => m.id === item.maquinaria) || { nombre: `Maquinaria #${item.maquinaria}`, tarifa_diaria: 0, garantia_fija: 0 },
        inicio: item.fecha_inicio,
        fin: item.fecha_fin,
        dias: Number(item.dias_arriendo),
        costo: Number(item.costo_calculado)
      }));
      updateCartBadge();
    }
  } catch (err) { showToast('No se pudo cargar el carro guardado.', 'error'); }
}

// Catálogo y stock siempre vienen del servidor para evitar precios y cantidades obsoletos.
async function fetchCatalog() {
  if (isLocalFile()) {
    document.getElementById('localModeNote').hidden = false;
    document.getElementById('catalogGrid').innerHTML = '<p class="catalog-message">Abre MaquiRent desde <strong>http://127.0.0.1:8000/</strong> para conectar con el inventario y usar tu cuenta.</p>';
    document.getElementById('catalogCount').textContent = 'API no conectada';
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/maquinarias/`);
    if (!res.ok) throw new Error('catalog unavailable');
    const payload = await res.json();
    const machines = Array.isArray(payload) ? payload : payload.results || [];
    MACHINE_CATALOG.splice(0, MACHINE_CATALOG.length, ...machines.map(machine => ({
      ...machine,
      img: machine.imagen_url || FALLBACK_MACHINE_IMAGE
    })));
    renderFilters();
    renderCatalog(currentFilter);
  } catch (err) {
    // Sin datos reales se muestra un estado claro, nunca el inventario ficticio como si fuera real.
    document.getElementById('catalogGrid').innerHTML = '<p class="catalog-message">No se pudo cargar el inventario. Intenta recargar la página.</p>';
    document.getElementById('catalogCount').textContent = 'Inventario no disponible';
  }
}

function restoreSession() {
  if (authToken) document.getElementById('loginBtn').textContent = 'Cerrar sesión';
  updateAccountInterface();
}

const contractTransitions = {
  PENDIENTE: [['PAGADO', 'Confirmar pago'], ['CANCELADO', 'Cancelar']],
  PAGADO: [['ENTREGADO', 'Marcar entregado'], ['CANCELADO', 'Cancelar']],
  ENTREGADO: [['COMPLETADO', 'Marcar completado'], ['CANCELADO', 'Cancelar']]
};
const contractStateLabels = {
  PENDIENTE: 'Pendiente', PAGADO: 'Pagado', ENTREGADO: 'Entregado',
  COMPLETADO: 'Completado', CANCELADO: 'Cancelado'
};

// Muestra las solicitudes visibles para el Ejecutivo y las transiciones permitidas por contrato.
async function fetchAdminOrders() {
  const list = document.getElementById('adminOrders');
  try {
    const response = await apiFetch(`${API_BASE}/api/contratos/`);
    if (!response.ok) throw new Error('No se pudieron cargar los contratos.');
    const payload = await response.json();
    const contracts = Array.isArray(payload) ? payload : payload.results || [];
    document.getElementById('adminOrderCount').textContent = contracts.length;
    const pending = contracts.filter(order => order.estado === 'PENDIENTE').length;
    const active = contracts.filter(order => ['PAGADO', 'ENTREGADO'].includes(order.estado)).length;
    document.getElementById('adminStats').innerHTML = `
      <div class="admin-stat"><strong>${pending}</strong><span>Pendientes</span></div>
      <div class="admin-stat"><strong>${active}</strong><span>En curso</span></div>
      <div class="admin-stat"><strong>${contracts.length}</strong><span>Contratos</span></div>`;

    if (!contracts.length) {
      list.innerHTML = '<p class="catalog-message">Todavía no hay contratos registrados.</p>';
      return;
    }
    list.innerHTML = contracts.map(order => {
      const state = contractStateLabels[order.estado] || order.estado;
      const details = (order.detalles || []).map(detail => {
        const machine = MACHINE_CATALOG.find(item => item.id === detail.maquinaria);
        const name = machine?.nombre || `Maquinaria #${detail.maquinaria ?? 'eliminada'}`;
        return `<div>${escapeHtml(name)} · ${escapeHtml(detail.fecha_inicio)} al ${escapeHtml(detail.fecha_fin)}</div>`;
      }).join('');
      const actions = (contractTransitions[order.estado] || []).map(([nextState, label]) =>
        `<button class="admin-action-btn ${nextState === 'CANCELADO' ? 'admin-action-danger' : ''}" type="button" data-order-id="${Number(order.id)}" data-next-state="${nextState}">${label}</button>`
      ).join('');
      const created = order.fecha_creacion ? new Date(order.fecha_creacion).toLocaleString('es-CL') : 'Fecha no disponible';
      return `<article class="admin-order">
        <div class="admin-order-top"><div><h4>Contrato #${Number(order.id)} · ${escapeHtml(order.cliente || 'Cliente')}</h4>
        <p class="admin-order-meta">Folio: ${escapeHtml(order.codigo_uuid || '')} · ${escapeHtml(order.cliente_email || '')} · ${escapeHtml(created)}</p></div>
        <span class="admin-order-status status-${String(order.estado).toLowerCase()}">${escapeHtml(state)}</span></div>
        <div class="admin-order-detail">${details || 'Sin equipos asociados.'}</div>
        <div class="admin-order-total">Total: ${fmt(order.total)}</div>
        ${actions ? `<div class="admin-order-actions">${actions}</div>` : ''}
      </article>`;
    }).join('');
  } catch (error) {
    list.innerHTML = `<p class="catalog-message">${escapeHtml(error.message || 'No se pudieron cargar los contratos.')}</p>`;
    document.getElementById('adminOrderCount').textContent = '—';
  }
}

function renderAdminMachines() {
  const list = document.getElementById('adminMachineList');
  list.innerHTML = MACHINE_CATALOG.map(machine => `
    <article class="admin-machine-row">
      <div><h4>${escapeHtml(machine.nombre)}</h4><p>${escapeHtml(machine.categoria)} · ${Number(machine.stock_disponible)} unidades · ${fmt(machine.tarifa_diaria)}/día</p></div>
      <div class="admin-machine-actions">
        <button type="button" data-edit-machine="${Number(machine.id)}">Editar</button>
        <button class="delete-machine" type="button" data-delete-machine="${Number(machine.id)}">Eliminar</button>
      </div>
    </article>`).join('');
}

async function loadExecutiveDashboard() {
  if (!authToken || !isExecutiveSession()) return;
  await fetchCatalog();
  await fetchAdminOrders();
  renderAdminMachines();
}

async function changeContractState(contractId, nextState, button) {
  button.disabled = true;
  try {
    const response = await apiFetch(`${API_BASE}/api/contratos/${contractId}/estado/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: nextState })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(errorText(error));
    }
    showToast(`Contrato #${contractId}: ${contractStateLabels[nextState]}.`);
    await loadExecutiveDashboard();
  } catch (error) {
    showToast(error.message || 'No se pudo actualizar el contrato.', 'error');
    button.disabled = false;
  }
}

document.getElementById('refreshAdmin').addEventListener('click', loadExecutiveDashboard);
document.getElementById('adminOrders').addEventListener('click', event => {
  const button = event.target.closest('[data-order-id]');
  if (button) changeContractState(Number(button.dataset.orderId), button.dataset.nextState, button);
});

function resetAdminMachineForm() {
  document.getElementById('adminMachineForm').reset();
  document.getElementById('adminMachineId').value = '';
  document.getElementById('adminMachineError').textContent = '';
  document.getElementById('saveMachineBtn').textContent = 'Agregar maquinaria';
  document.getElementById('cancelMachineEdit').hidden = true;
}

document.getElementById('cancelMachineEdit').addEventListener('click', resetAdminMachineForm);
document.getElementById('adminMachineList').addEventListener('click', async event => {
  const editButton = event.target.closest('[data-edit-machine]');
  const deleteButton = event.target.closest('[data-delete-machine]');
  if (editButton) {
    const machine = MACHINE_CATALOG.find(item => item.id === Number(editButton.dataset.editMachine));
    if (!machine) return;
    document.getElementById('adminMachineId').value = machine.id;
    document.getElementById('adminMachineName').value = machine.nombre;
    document.getElementById('adminMachineCategory').value = machine.categoria;
    document.getElementById('adminMachineRate').value = machine.tarifa_diaria;
    document.getElementById('adminMachineGuarantee').value = machine.garantia_fija;
    document.getElementById('adminMachineStock').value = machine.stock_disponible;
    document.getElementById('adminMachineImage').value = machine.imagen_url || '';
    document.getElementById('saveMachineBtn').textContent = 'Guardar cambios';
    document.getElementById('cancelMachineEdit').hidden = false;
    document.getElementById('adminMachineName').focus();
    return;
  }
  if (!deleteButton) return;
  const machineId = Number(deleteButton.dataset.deleteMachine);
  const machine = MACHINE_CATALOG.find(item => item.id === machineId);
  if (!machine || !window.confirm(`¿Eliminar ${machine.nombre} del catálogo?`)) return;
  deleteButton.disabled = true;
  try {
    const response = await apiFetch(`${API_BASE}/api/maquinarias/${machineId}/`, { method: 'DELETE' });
    if (!response.ok) throw new Error('No se pudo eliminar la maquinaria.');
    await loadExecutiveDashboard();
    showToast('Maquinaria eliminada del catálogo.');
  } catch (error) {
    showToast(error.message, 'error');
    deleteButton.disabled = false;
  }
});

document.getElementById('adminMachineForm').addEventListener('submit', async event => {
  event.preventDefault();
  const errorBox = document.getElementById('adminMachineError');
  const button = document.getElementById('saveMachineBtn');
  errorBox.textContent = '';
  const machineId = document.getElementById('adminMachineId').value;
  const data = {
    nombre: document.getElementById('adminMachineName').value.trim(),
    categoria: document.getElementById('adminMachineCategory').value.trim(),
    tarifa_diaria: document.getElementById('adminMachineRate').value,
    garantia_fija: document.getElementById('adminMachineGuarantee').value,
    stock_disponible: Number(document.getElementById('adminMachineStock').value),
    imagen_url: document.getElementById('adminMachineImage').value.trim()
  };
  button.disabled = true;
  try {
    const response = await apiFetch(`${API_BASE}/api/maquinarias/${machineId ? `${machineId}/` : ''}`, {
      method: machineId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(errorText(await response.json()));
    resetAdminMachineForm();
    await loadExecutiveDashboard();
    showToast(machineId ? 'Maquinaria actualizada.' : 'Maquinaria agregada al catálogo.');
  } catch (error) {
    errorBox.textContent = error.message || 'No se pudo guardar la maquinaria.';
  } finally {
    button.disabled = false;
  }
});

// Menú móvil accesible con teclado y táctil.
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');
navToggle.addEventListener('click', () => {
  const expanded = navToggle.getAttribute('aria-expanded') === 'true';
  navToggle.setAttribute('aria-expanded', String(!expanded));
  navToggle.setAttribute('aria-label', expanded ? 'Abrir menú' : 'Cerrar menú');
  navLinks.classList.toggle('open', !expanded);
});
navLinks.addEventListener('click', (event) => {
  if (event.target.closest('a')) { navLinks.classList.remove('open'); navToggle.setAttribute('aria-expanded', 'false'); }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    const modal = document.querySelector('.modal-overlay.active');
    if (modal) closeModal(modal.id);
    navLinks.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  }
});

// ===== CIERRE DE MODALES =====
document.getElementById('closeLogin').addEventListener('click', () => closeModal('loginModal'));
document.getElementById('closeCart').addEventListener('click', () => closeModal('cartModal'));
document.getElementById('closeAddCart').addEventListener('click', () => closeModal('addCartModal'));

// Cerrar al clicar el overlay
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeModal(overlay.id);
    }
  });
});

// ===== INICIALIZACIÓN =====
restoreSession();
// Evita seleccionar fechas pasadas desde el navegador; el servidor repite esta validación.
document.getElementById('fechaInicio').min = localISODate();
document.getElementById('fechaFin').min = localISODate();
fetchCatalog().then(() => {
  if (!authToken) return;
  if (isExecutiveSession()) loadExecutiveDashboard();
  else fetchCartFromBackend();
});
// Refresca el stock cuando el usuario vuelve a la pestaña después de otra gestión.
window.addEventListener('focus', fetchCatalog);
