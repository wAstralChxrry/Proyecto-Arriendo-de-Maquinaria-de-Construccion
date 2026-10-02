/* ============================================================
   MAQUIRENT - LÓGICA DE LA APLICACIÓN FRONTEND
   Conecta con el backend Django REST Framework mediante fetch()
   ============================================================ */

const API_BASE = 'http://127.0.0.1:8000';

// ===== CATÁLOGO DE MAQUINARIA (datos de demostración + fotos de Unsplash) =====
const MACHINE_CATALOG = [
  {
    id: 1, nombre: 'Excavadora Caterpillar 320', categoria: 'Excavación',
    tarifa_diaria: 85000, garantia_fija: 150000, stock_disponible: 3,
    img: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 2, nombre: 'Grúa Torre Potain MDT 389', categoria: 'Elevación',
    tarifa_diaria: 120000, garantia_fija: 300000, stock_disponible: 1,
    img: 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 3, nombre: 'Bulldozer Komatsu D65', categoria: 'Movimiento de Tierra',
    tarifa_diaria: 70000, garantia_fija: 120000, stock_disponible: 2,
    img: 'https://images.unsplash.com/photo-1581094288338-2314dddb7ece?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 4, nombre: 'Rodillo Compactador Bomag', categoria: 'Compactación',
    tarifa_diaria: 45000, garantia_fija: 80000, stock_disponible: 4,
    img: 'https://images.unsplash.com/photo-1587293852726-70cdb56c2866?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 5, nombre: 'Retroexcavadora JCB 3CX', categoria: 'Excavación',
    tarifa_diaria: 55000, garantia_fija: 100000, stock_disponible: 5,
    img: 'https://images.unsplash.com/photo-1590496793929-36417d3117de?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 6, nombre: 'Camión Pluma Hiab 400', categoria: 'Transporte',
    tarifa_diaria: 60000, garantia_fija: 90000, stock_disponible: 0,
    img: 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 7, nombre: 'Minicargador Bobcat S650', categoria: 'Movimiento de Tierra',
    tarifa_diaria: 35000, garantia_fija: 60000, stock_disponible: 6,
    img: 'https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=600&auto=format&fit=crop&q=75'
  },
  {
    id: 8, nombre: 'Grúa Horquilla Yale GDP50', categoria: 'Elevación',
    tarifa_diaria: 28000, garantia_fija: 50000, stock_disponible: 3,
    img: 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600&auto=format&fit=crop&q=75'
  },
];

// ===== ESTADO GLOBAL =====
let currentFilter = 'all';
let cart = [];
let authToken = null;
let selectedMachine = null;

// ===== UTILIDADES =====
const fmt = (n) => `$${Number(n).toLocaleString('es-CL')}`;

function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  setTimeout(() => { toast.classList.remove('show'); }, 3000);
}

function openModal(id) {
  document.getElementById(id).classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.remove('active');
  document.body.style.overflow = '';
}

// ===== NAVBAR SCROLL =====
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  nav.classList.toggle('scrolled', window.scrollY > 30);
});

// ===== RENDERIZAR CATÁLOGO =====
function renderCatalog(filter = 'all') {
  const grid = document.getElementById('catalogGrid');
  const filtered = filter === 'all' ? MACHINE_CATALOG : MACHINE_CATALOG.filter(m => m.categoria === filter);

  grid.innerHTML = filtered.map(machine => {
    const stockOk = machine.stock_disponible > 0;
    return `
      <div class="machine-card" data-cat="${machine.categoria}">
        <div class="card-img-wrapper">
          <img src="${machine.img}" alt="${machine.nombre}" loading="lazy" />
          <span class="card-badge">${machine.categoria}</span>
          <span class="card-stock ${stockOk ? 'stock-ok' : 'stock-out'}">
            ${stockOk ? `${machine.stock_disponible} disponibles` : 'Sin stock'}
          </span>
        </div>
        <div class="card-body">
          <h3 class="card-title">${machine.nombre}</h3>
          <p class="card-tarifa">${fmt(machine.tarifa_diaria)} <span>/ día</span></p>
          <p class="card-garantia">Garantía fija: ${fmt(machine.garantia_fija)}</p>
          <button class="card-add-btn" 
            onclick="handleAddClick(${machine.id})"
            ${!stockOk ? 'disabled' : ''}>
            ${stockOk ? '+ Agregar al Carro' : 'Sin Disponibilidad'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// ===== FILTROS =====
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderCatalog(currentFilter);
  });
});

// ===== CLIC EN "AGREGAR AL CARRO" =====
function handleAddClick(machineId) {
  if (!authToken) {
    showToast('Debes iniciar sesión para arrendar.', 'error');
    openModal('loginModal');
    return;
  }
  selectedMachine = MACHINE_CATALOG.find(m => m.id === machineId);
  document.getElementById('addCartTitle').textContent = `Arrendar: ${selectedMachine.nombre}`;
  document.getElementById('addCartDesc').textContent = `${fmt(selectedMachine.tarifa_diaria)}/día + ${fmt(selectedMachine.garantia_fija)} de garantía`;
  document.getElementById('addCartError').textContent = '';
  document.getElementById('costPreview').style.display = 'none';
  document.getElementById('addCartForm').reset();
  openModal('addCartModal');
}

// ===== CALCULAR COSTO EN TIEMPO REAL =====
function calcCost() {
  if (!selectedMachine) return;
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

  // Intentar llamar al backend real
  try {
    const res = await fetch(`${API_BASE}/api/carro-arriendo/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
      body: JSON.stringify({ maquinaria: selectedMachine.id, fecha_inicio: inicio, fecha_fin: fin })
    });

    if (res.ok) {
      const data = await res.json();
      addToLocalCart(selectedMachine, inicio, fin);
      closeModal('addCartModal');
      showToast(`${selectedMachine.nombre} agregado al carro.`);
      return;
    }
  } catch (err) { /* si backend no está disponible, modo demo */ }

  // Modo demo (sin backend activo)
  addToLocalCart(selectedMachine, inicio, fin);
  closeModal('addCartModal');
  showToast(`${selectedMachine.nombre} agregado al carro.`);
});

function addToLocalCart(machine, inicio, fin) {
  const dias = Math.ceil((new Date(fin) - new Date(inicio)) / 86400000);
  const costo = machine.tarifa_diaria * dias + machine.garantia_fija;
  cart.push({ machine, inicio, fin, dias, costo });
  updateCartBadge();
}

function updateCartBadge() {
  document.getElementById('cartBadge').textContent = cart.length;
}

// ===== RENDER CARRO =====
function renderCart() {
  const listEl = document.getElementById('cartItems');
  const totalEl = document.getElementById('cartTotal');

  if (cart.length === 0) {
    listEl.innerHTML = '<div class="cart-empty">Tu carro esta vacio.</div>';
    totalEl.textContent = '$0';
    return;
  }

  listEl.innerHTML = cart.map((item, i) => `
    <div class="cart-item">
      <div class="cart-item-info">
        <h4>${item.machine.nombre}</h4>
        <p>${item.inicio} → ${item.fin} · ${item.dias} días</p>
      </div>
      <span class="cart-item-price">${fmt(item.costo)}</span>
    </div>
  `).join('');

  const total = cart.reduce((acc, i) => acc + i.costo, 0);
  totalEl.textContent = fmt(total);
}

// ===== BOTÓN CARRO =====
document.getElementById('cartBtn').addEventListener('click', () => {
  renderCart();
  openModal('cartModal');
});

// ===== CHECKOUT =====
document.getElementById('checkoutBtn').addEventListener('click', async () => {
  if (cart.length === 0) return;

  try {
    const res = await fetch(`${API_BASE}/api/contratos/checkout/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      cart = [];
      updateCartBadge();
      closeModal('cartModal');
      showToast('Contrato generado correctamente. Estado: PENDIENTE.');
      return;
    }
  } catch (err) { /* modo demo */ }

  // Demo
  cart = [];
  updateCartBadge();
  closeModal('cartModal');
  showToast('Contrato generado. Estado: PENDIENTE de pago.');
});

// ===== LOGIN =====
document.getElementById('loginBtn').addEventListener('click', () => openModal('loginModal'));
document.getElementById('registerBtn').addEventListener('click', () => {
  showToast('Registro disponible en: /admin (superusuario) o crear usuarios desde el backend.', 'success');
});

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('loginUser').value;
  const password = document.getElementById('loginPass').value;
  const errEl = document.getElementById('loginError');
  errEl.textContent = '';

  try {
    const res = await fetch(`${API_BASE}/api/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();

    if (res.ok) {
      authToken = data.access;
      closeModal('loginModal');
      document.getElementById('loginBtn').textContent = `${username}`;
      document.getElementById('registerBtn').style.display = 'none';
      showToast(`Bienvenido, ${username}!`);

      // Cargar carro real desde el backend
      fetchCartFromBackend();
    } else {
      errEl.textContent = 'Usuario o contraseña incorrectos.';
    }
  } catch (err) {
    errEl.textContent = 'No se pudo conectar con el servidor. Verifica que esté activo.';
  }
});

// ===== CARGAR CARRO DESDE BACKEND =====
async function fetchCartFromBackend() {
  if (!authToken) return;
  try {
    const res = await fetch(`${API_BASE}/api/carro-arriendo/`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      // Sincronizar items del backend con el estado local
      const items = data.items || (data[0] && data[0].items) || [];
      cart = items.map(item => ({
        machine: MACHINE_CATALOG.find(m => m.id === item.maquinaria) || { nombre: `Maquinaria #${item.maquinaria}`, tarifa_diaria: 0, garantia_fija: 0 },
        inicio: item.fecha_inicio,
        fin: item.fecha_fin,
        dias: item.dias_arriendo,
        costo: item.costo_calculado
      }));
      updateCartBadge();
    }
  } catch (err) { /* silencioso */ }
}

// ===== CIERRE DE MODALES =====
document.getElementById('closeLogin').addEventListener('click', () => closeModal('loginModal'));
document.getElementById('closeCart').addEventListener('click', () => closeModal('cartModal'));
document.getElementById('closeAddCart').addEventListener('click', () => closeModal('addCartModal'));

// Cerrar al clicar el overlay
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
});

// ===== INICIALIZACIÓN =====
renderCatalog();
