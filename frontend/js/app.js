const API_BASE = "/api";

// ---------------------------------------------------------------------------
// Auth & API Helper
// ---------------------------------------------------------------------------
function getToken() {
  return localStorage.getItem('token');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('user'));
  } catch (e) {
    return null;
  }
}

function saveUser(user) {
  if (user) {
    localStorage.setItem('user', JSON.stringify(user));
  }
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'login.html';
}

async function fetchWithAuth(url, options = {}) {
  const token = getToken();
  if (!token) {
    window.location.href = 'login.html';
    return null;
  }

  const headers = options.headers || {};
  headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  options.headers = headers;

  const res = await fetch(url, options);

  if (res.status === 401) {
    logout();
    return null;
  }

  if (res.status === 403) {
    const data = await res.json();
    if (data.detail && (data.detail.includes("limite de teste") || data.detail.includes("R$ 50"))) {
      openModal('modal-upgrade');
    }
    throw new Error(data.detail || "Acesso negado.");
  }

  return res;
}

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------
function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleDateString('pt-BR');
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `badge badge-${type}`;
  toast.style.padding = '0.8rem 1.2rem';
  toast.style.fontSize = '0.9rem';
  toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function labelModalidade(modalidade, curto = false) {
  if (modalidade === 'juros_final') {
    return curto ? '💡 Juros + Capital Final' : '💡 Apenas Juros Mensais + Capital no Final';
  }
  return curto ? '📊 Tabela Price' : '📊 Parcelado Normal (Tabela Price)';
}

function formatInstagramLink(ig) {
  if (!ig || !ig.trim()) return '-';
  let handle = ig.trim();
  let url = handle;

  if (handle.startsWith('@')) {
    const user = handle.substring(1);
    url = `https://instagram.com/${user}`;
  } else if (!handle.startsWith('http://') && !handle.startsWith('https://')) {
    url = `https://instagram.com/${handle}`;
    handle = `@${handle}`;
  } else {
    // É URL completa
    const parts = handle.split('instagram.com/');
    if (parts.length > 1) {
      handle = `@${parts[1].replace('/', '')}`;
    }
  }

  return `<a href="${url}" target="_blank" style="color: #e1306c; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
    📷 ${handle}
  </a>`;
}

function cleanPhoneNumber(phone) {
  if (!phone) return '';
  return phone.replace(/\D/g, '');
}

// ---------------------------------------------------------------------------
// Global State
// ---------------------------------------------------------------------------
let state = {
  clientes: [],
  emprestimos: [],
  dashboard: {},
  activeEmprestimo: null,
  currentUser: null
};

// ---------------------------------------------------------------------------
// App Init / Navigation
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  setupNavigation();
  updateUserDisplay();
  await loadClientes();
  await loadDashboard();
  await loadEmprestimos();
}

function updateUserDisplay() {
  const user = getUser();
  state.currentUser = user;
  if (!user) return;

  const nomeEl = document.getElementById('user-display-nome');
  const emailEl = document.getElementById('user-display-email');
  const badgeEl = document.getElementById('user-display-badge');

  if (nomeEl) nomeEl.innerText = user.nome;
  if (emailEl) emailEl.innerText = user.email;

  if (badgeEl) {
    let badgeClass = 'badge-warning';
    let badgeText = 'TESTE (TRIAL)';
    if (user.status_assinatura === 'ativo') {
      badgeClass = 'badge-success';
      badgeText = 'ASSINANTE ATIVO';
    } else if (user.status_assinatura === 'bloqueado') {
      badgeClass = 'badge-danger';
      badgeText = 'BLOQUEADO';
    }
    badgeEl.innerHTML = `<span class="badge ${badgeClass}">${badgeText}</span>`;
  }

  if (user.is_admin) {
    const adminNavItem = document.getElementById('nav-item-admin');
    if (adminNavItem) adminNavItem.style.display = 'block';
  }
}

function setupNavigation() {
  const navBtns = document.querySelectorAll('.nav-item button');
  navBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));

  const activeNavBtn = document.querySelector(`[data-tab="${tabId}"]`);
  const activeTab = document.getElementById(`tab-${tabId}`);

  if (activeNavBtn && activeNavBtn.parentElement) activeNavBtn.parentElement.classList.add('active');
  if (activeTab) activeTab.classList.add('active');

  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'clientes') loadClientes();
  if (tabId === 'emprestimos') loadEmprestimos();
  if (tabId === 'admin') loadAdminUsuarios();
}

// ---------------------------------------------------------------------------
// API Calls - Dashboard
// ---------------------------------------------------------------------------
async function loadDashboard() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/dashboard/`);
    if (!res) return;
    const data = await res.json();
    state.dashboard = data;

    document.getElementById('stat-clientes').innerText = data.total_clientes;
    document.getElementById('stat-emprestimos-ativos').innerText = data.total_emprestimos_ativos;
    document.getElementById('stat-valor-emprestado').innerText = formatCurrency(data.valor_total_emprestado);
    document.getElementById('stat-valor-receber').innerText = formatCurrency(data.valor_total_a_receber);
    document.getElementById('stat-valor-recebido').innerText = formatCurrency(data.valor_total_recebido);
    document.getElementById('stat-parcelas-vencidas').innerText = data.parcelas_vencidas;

    const banner = document.getElementById('trial-alert-banner');
    const bannerText = document.getElementById('trial-alert-text');
    if (banner) {
      if (data.status_assinatura === 'trial') {
        banner.style.display = 'flex';
        if (bannerText) {
          bannerText.innerHTML = `Você utilizou <strong>${data.total_clientes}/2</strong> clientes no teste grátis. Assine para liberação ilimitada!`;
        }
      } else {
        banner.style.display = 'none';
      }
    }
  } catch (err) {
    console.error("Erro ao carregar dashboard:", err);
  }
}

// ---------------------------------------------------------------------------
// API Calls - Clientes
// ---------------------------------------------------------------------------
async function loadClientes() {
  try {
    const search = document.getElementById('search-cliente')?.value || '';
    const url = search ? `${API_BASE}/clientes/?busca=${encodeURIComponent(search)}` : `${API_BASE}/clientes/`;
    const res = await fetchWithAuth(url);
    if (!res) return;
    const data = await res.json();
    state.clientes = data;
    renderClientesTable(data);
    updateClienteSelects(data);
  } catch (err) {
    console.error("Erro ao carregar clientes:", err);
  }
}

function renderClientesTable(clientes) {
  const tbody = document.getElementById('tbody-clientes');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (clientes.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">Nenhum cliente cadastrado.</td></tr>`;
    return;
  }

  clientes.forEach(c => {
    // Formatar Telefones com Botão de Ligar (tel:) e WhatsApp
    let phonesHTML = '';
    const telList = [
      { num: c.telefone, label: 'Principal' },
      { num: c.telefone_2, label: 'Parente 1' },
      { num: c.telefone_3, label: 'Parente 2' }
    ].filter(t => t.num && t.num.trim());

    if (telList.length === 0) {
      phonesHTML = '<span style="color: var(--text-muted); font-size: 0.8rem;">Sem telefone</span>';
    } else {
      phonesHTML = telList.map(t => {
        const clean = cleanPhoneNumber(t.num);
        let waNumber = clean;
        if (clean.length === 10 || clean.length === 11) waNumber = '55' + clean;

        return `
          <div style="font-size: 0.82rem; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <strong style="color: #cbd5e1;">${t.label}:</strong> ${t.num}
            <a href="tel:${clean}" class="btn btn-secondary btn-sm" style="padding: 2px 6px; font-size: 0.72rem;" title="Ligar para ${t.num}">📞 Ligar</a>
            <a href="https://wa.me/${waNumber}" target="_blank" class="btn btn-whatsapp btn-sm" style="padding: 2px 6px; font-size: 0.72rem;" title="Abrir WhatsApp com ${t.num}">📱 Whats</a>
          </div>
        `;
      }).join('');
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${c.id}</strong></td>
      <td>${c.nome}</td>
      <td>${c.cpf}</td>
      <td>${formatInstagramLink(c.instagram)}</td>
      <td>${phonesHTML}</td>
      <td><span class="badge badge-${c.ativo ? 'success' : 'danger'}">${c.ativo ? 'Ativo' : 'Inativo'}</span></td>
      <td class="text-right">
        <button class="btn btn-secondary btn-sm" onclick="abrirEditarCliente(${c.id})">✏️ Editar</button>
        <button class="btn btn-danger btn-sm" onclick="deletarCliente(${c.id})">🗑️ Excluir</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function updateClienteSelects(clientes) {
  const select = document.getElementById('emp-cliente-select');
  if (!select) return;
  select.innerHTML = '<option value="">Selecione um cliente...</option>';
  clientes.forEach(c => {
    select.innerHTML += `<option value="${c.id}">${c.nome} (${c.cpf})</option>`;
  });
}

function openNovoClienteModal() {
  const user = getUser();
  if (user && user.status_assinatura === 'trial' && state.clientes.length >= 2) {
    openModal('modal-upgrade');
    return;
  }
  openModal('modal-novo-cliente');
}

async function handleSalvarCliente(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    nome: form.nome.value.trim(),
    cpf: form.cpf.value.trim(),
    instagram: form.instagram.value.trim() || null,
    telefone: form.telefone.value.trim() || null,
    telefone_2: form.telefone_2.value.trim() || null,
    telefone_3: form.telefone_3.value.trim() || null,
    endereco: form.endereco.value.trim() || null,
    observacoes: form.observacoes.value.trim() || null
  };

  try {
    const res = await fetchWithAuth(`${API_BASE}/clientes/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (!res) return;

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erro ao cadastrar cliente');
    }

    showToast('Cliente cadastrado com sucesso!');
    closeModal('modal-novo-cliente');
    form.reset();
    await loadClientes();
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// Editar Cliente
// ---------------------------------------------------------------------------
function abrirEditarCliente(id) {
  const cliente = state.clientes.find(c => c.id === id);
  if (!cliente) {
    showToast("Cliente não encontrado", "danger");
    return;
  }

  document.getElementById('edit-cliente-id').value = cliente.id;
  document.getElementById('edit-cliente-nome').value = cliente.nome || '';
  document.getElementById('edit-cliente-cpf').value = cliente.cpf || '';
  document.getElementById('edit-cliente-instagram').value = cliente.instagram || '';
  document.getElementById('edit-cliente-telefone').value = cliente.telefone || '';
  document.getElementById('edit-cliente-telefone-2').value = cliente.telefone_2 || '';
  document.getElementById('edit-cliente-telefone-3').value = cliente.telefone_3 || '';
  document.getElementById('edit-cliente-endereco').value = cliente.endereco || '';
  document.getElementById('edit-cliente-observacoes').value = cliente.observacoes || '';

  openModal('modal-editar-cliente');
}

async function handleAtualizarCliente(e) {
  e.preventDefault();
  const id = document.getElementById('edit-cliente-id').value;
  const payload = {
    nome: document.getElementById('edit-cliente-nome').value.trim(),
    cpf: document.getElementById('edit-cliente-cpf').value.trim(),
    instagram: document.getElementById('edit-cliente-instagram').value.trim() || null,
    telefone: document.getElementById('edit-cliente-telefone').value.trim() || null,
    telefone_2: document.getElementById('edit-cliente-telefone-2').value.trim() || null,
    telefone_3: document.getElementById('edit-cliente-telefone-3').value.trim() || null,
    endereco: document.getElementById('edit-cliente-endereco').value.trim() || null,
    observacoes: document.getElementById('edit-cliente-observacoes').value.trim() || null
  };

  try {
    const res = await fetchWithAuth(`${API_BASE}/clientes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });

    if (!res) return;

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erro ao atualizar cliente');
    }

    showToast('Dados do cliente atualizados com sucesso!');
    closeModal('modal-editar-cliente');
    await loadClientes();
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// Deletar Cliente (Corrigido com validação e confirmação)
// ---------------------------------------------------------------------------
async function deletarCliente(id) {
  const cliente = state.clientes.find(c => c.id === id);
  const nome = cliente ? cliente.nome : `#${id}`;

  const confirmou = window.confirm(`ATENÇÃO: Deseja realmente excluir o cliente "${nome}"?\nEsta ação removerá o cliente e seus registros vinculados do banco de dados.`);
  if (!confirmou) return;

  try {
    const res = await fetchWithAuth(`${API_BASE}/clientes/${id}`, { method: 'DELETE' });
    if (!res) return;

    if (!res.ok && res.status !== 204) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Erro ao excluir cliente");
    }

    showToast(`Cliente "${nome}" foi excluído com sucesso!`);
    await loadClientes();
    await loadDashboard();
    await loadEmprestimos();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// API Calls - Empréstimos
// ---------------------------------------------------------------------------
async function loadEmprestimos() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/emprestimos/`);
    if (!res) return;
    const data = await res.json();
    state.emprestimos = data;
    renderEmprestimosTable(data);
  } catch (err) {
    console.error("Erro ao carregar empréstimos:", err);
  }
}

function renderEmprestimosTable(emprestimos) {
  const tbody = document.getElementById('tbody-emprestimos');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (emprestimos.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted);">Nenhum empréstimo cadastrado.</td></tr>`;
    return;
  }

  emprestimos.forEach(e => {
    const cliente = state.clientes.find(c => c.id === e.cliente_id);
    const modalidade = e.modalidade || 'price';
    const isJurosFinal = modalidade === 'juros_final';

    const parcelaLabel = isJurosFinal
      ? `${formatCurrency(e.valor_parcela)}/mês (juros) + ${formatCurrency(e.valor_principal)} no final`
      : `${formatCurrency(e.valor_parcela)} (${e.num_parcelas}x)`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${e.id}</strong></td>
      <td>${cliente ? cliente.nome : 'Cliente #' + e.cliente_id}</td>
      <td>${formatCurrency(e.valor_principal)}</td>
      <td>${e.taxa_juros}%</td>
      <td>
        <span class="badge" style="background: ${isJurosFinal ? 'rgba(99,102,241,0.25); color:#a5b4fc; border:1px solid rgba(99,102,241,0.5)' : 'rgba(16,185,129,0.15); color:#6ee7b7; border:1px solid rgba(16,185,129,0.4)'}">
          ${labelModalidade(modalidade, true)}
        </span>
      </td>
      <td style="font-size: 0.82rem; color: var(--text-muted);">${parcelaLabel}</td>
      <td><span class="badge badge-${e.status === 'ativo' ? 'warning' : 'success'}">${e.status.toUpperCase()}</span></td>
      <td class="text-right">
        <button class="btn btn-primary btn-sm" onclick="verCarneEmprestimo(${e.id})">Ver Carnê</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function handleSalvarEmprestimo(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    cliente_id: parseInt(form.cliente_id.value),
    valor_principal: parseFloat(form.valor_principal.value),
    taxa_juros: parseFloat(form.taxa_juros.value),
    num_parcelas: parseInt(form.num_parcelas.value),
    modalidade: form.modalidade.value || 'price',
    descricao: form.descricao.value.trim() || null
  };

  try {
    const res = await fetchWithAuth(`${API_BASE}/emprestimos/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (!res) return;

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erro ao gerar empréstimo');
    }

    const data = await res.json();
    showToast('Empréstimo e carnê gerados com sucesso!');
    closeModal('modal-novo-emprestimo');
    form.reset();
    document.getElementById('info-juros-final').style.display = 'none';
    await loadEmprestimos();
    await loadDashboard();
    verCarneEmprestimo(data.id);
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

function onModalidadeChange() {
  const select = document.getElementById('emp-modalidade-select');
  const infoBox = document.getElementById('info-juros-final');
  if (!select || !infoBox) return;
  infoBox.style.display = select.value === 'juros_final' ? 'block' : 'none';
}

// ---------------------------------------------------------------------------
// Simulação
// ---------------------------------------------------------------------------
async function handleSimulacao() {
  const valor = parseFloat(document.getElementById('sim-valor').value) || 0;
  const taxa = parseFloat(document.getElementById('sim-taxa').value) || 0;
  const parcelas = parseInt(document.getElementById('sim-parcelas').value) || 0;
  const modalidade = document.getElementById('sim-modalidade')?.value || 'price';

  if (valor <= 0 || parcelas <= 0) return;

  const avisoEl = document.getElementById('sim-aviso-juros-final');
  const linhaUltima = document.getElementById('sim-linha-ultima');
  const labelParcela = document.getElementById('sim-label-parcela');

  if (modalidade === 'juros_final') {
    if (avisoEl) avisoEl.style.display = 'block';
    if (linhaUltima) linhaUltima.style.display = 'flex';
    if (labelParcela) labelParcela.innerText = 'Parcelas Mensais de Juros (1 a ' + (parcelas - 1) + '):';
  } else {
    if (avisoEl) avisoEl.style.display = 'none';
    if (linhaUltima) linhaUltima.style.display = 'none';
    if (labelParcela) labelParcela.innerText = 'Valor da Parcela:';
  }

  try {
    const res = await fetch(`${API_BASE}/emprestimos/simular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ valor, taxa_juros: taxa, num_parcelas: parcelas, modalidade })
    });
    const data = await res.json();

    document.getElementById('sim-res-parcela').innerText = formatCurrency(data.valor_parcela);
    document.getElementById('sim-res-total').innerText = formatCurrency(data.valor_total);
    document.getElementById('sim-res-juros').innerText = formatCurrency(data.total_juros);

    if (modalidade === 'juros_final') {
      const ultimaParcelaValor = data.valor_parcela + valor;
      const ultimaEl = document.getElementById('sim-res-ultima');
      if (ultimaEl) ultimaEl.innerText = formatCurrency(ultimaParcelaValor);
    }
  } catch (err) {
    console.error("Erro na simulação:", err);
  }
}

// ---------------------------------------------------------------------------
// Detalhes do Carnê / Pagamento & Cobrança WhatsApp
// ---------------------------------------------------------------------------
async function verCarneEmprestimo(id) {
  try {
    const res = await fetchWithAuth(`${API_BASE}/emprestimos/${id}`);
    if (!res) return;
    const emp = await res.json();
    state.activeEmprestimo = emp;
    const cliente = state.clientes.find(c => c.id === emp.cliente_id);
    const clienteNome = emp.cliente?.nome || cliente?.nome || 'Cliente';
    const modalidade = emp.modalidade || 'price';
    const isJurosFinal = modalidade === 'juros_final';

    document.getElementById('carne-cliente-nome').innerText = clienteNome;

    if (isJurosFinal) {
      const jurosMensais = emp.valor_parcela;
      const ultimaParcela = jurosMensais + emp.valor_principal;
      document.getElementById('carne-info-resumo').innerText =
        `Principal: ${formatCurrency(emp.valor_principal)} | Juros mensais: ${formatCurrency(jurosMensais)}/mês (${emp.num_parcelas - 1}x) | Última parcela: ${formatCurrency(ultimaParcela)} | Total: ${formatCurrency(emp.valor_total)}`;
    } else {
      document.getElementById('carne-info-resumo').innerText =
        `${formatCurrency(emp.valor_principal)} em ${emp.num_parcelas}x de ${formatCurrency(emp.valor_parcela)} (Total: ${formatCurrency(emp.valor_total)})`;
    }

    const modEl = document.getElementById('carne-info-modalidade');
    if (modEl) {
      modEl.innerHTML = `<span style="font-size:0.8rem; color: ${isJurosFinal ? '#a5b4fc' : '#6ee7b7'};">${labelModalidade(modalidade)}</span>`;
    }

    const aviso = document.getElementById('carne-aviso-juros-final');
    const thJuros = document.getElementById('carne-th-juros');
    const thAmort = document.getElementById('carne-th-amort');
    if (aviso) aviso.style.display = isJurosFinal ? 'block' : 'none';
    if (thJuros) thJuros.style.display = isJurosFinal ? '' : 'none';
    if (thAmort) thAmort.style.display = isJurosFinal ? '' : 'none';

    const tbody = document.getElementById('carne-parcelas-tbody');
    tbody.innerHTML = '';

    emp.parcelas.forEach(p => {
      const isVencida = !p.paga && new Date(p.data_vencimento) < new Date();
      const isUltima = (p.numero === emp.num_parcelas) && isJurosFinal;

      let tipoBadge = '';
      if (isJurosFinal) {
        tipoBadge = isUltima
          ? `<span style="font-size:0.72rem; padding:2px 6px; background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid rgba(245,158,11,0.4); border-radius:4px; margin-left:4px;">Juros + Capital</span>`
          : `<span style="font-size:0.72rem; padding:2px 6px; background:rgba(99,102,241,0.15); color:#a5b4fc; border:1px solid rgba(99,102,241,0.4); border-radius:4px; margin-left:4px;">Só Juros</span>`;
      }

      const colJuros = isJurosFinal ? `<td style="font-size:0.85rem; color:var(--text-muted);">${formatCurrency(p.juros || 0)}</td>` : '';
      const colAmort = isJurosFinal ? `<td style="font-size:0.85rem; color:var(--text-muted);">${formatCurrency(p.amortizacao || 0)}</td>` : '';

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>#${p.numero}</strong>${tipoBadge}</td>
        <td style="${isUltima ? 'color:#f59e0b; font-weight:600;' : ''}">${formatCurrency(p.valor)}</td>
        ${colJuros}
        ${colAmort}
        <td>${formatDate(p.data_vencimento)}</td>
        <td>
          ${p.paga ? `<span class="badge badge-success">PAGA (${(p.metodo_pagamento || 'pix').replace('_', ' ').toUpperCase()})</span><div style="font-size:0.75rem; color:#64748b; margin-top:2px;">${formatDate(p.data_pagamento)}</div>`
                   : isVencida ? `<span class="badge badge-danger">VENCIDA</span>`
                   : `<span class="badge badge-warning">PENDENTE</span>`}
        </td>
        <td class="text-right" style="display: flex; justify-content: flex-end; gap: 0.5rem; flex-wrap: wrap;">
          ${!p.paga ? `
            <button class="btn btn-primary btn-sm" onclick="abrirModalBaixarPagamento(${emp.id}, ${p.id}, ${p.valor})">Baixar Pagamento</button>
            <button class="btn btn-whatsapp btn-sm" onclick="iniciarCobrancaWhatsApp(${emp.cliente_id}, ${p.numero}, ${p.valor}, '${p.data_vencimento}', ${isVencida}, '${modalidade}', ${emp.num_parcelas}, ${emp.valor_principal})">📱 Cobrar via WhatsApp</button>
          ` : `<span style="color:var(--text-muted); font-size:0.8rem;">Paga</span>`}
        </td>
      `;
      tbody.appendChild(tr);
    });

    openModal('modal-carne');
  } catch (err) {
    showToast("Erro ao abrir carnê", "danger");
  }
}

// ---------------------------------------------------------------------------
// Seleção do Telefone para Envio no WhatsApp
// ---------------------------------------------------------------------------
function iniciarCobrancaWhatsApp(clienteId, parcelaNumero, parcelaValor, parcelaVencimento, isVencida, modalidade, totalParcelas, valorPrincipal) {
  const cliente = state.clientes.find(c => c.id === clienteId);
  if (!cliente) {
    showToast("Cliente não encontrado", "danger");
    return;
  }

  const disponiveis = [
    { label: 'Telefone Principal', num: cliente.telefone },
    { label: 'Secundário / Parente 1', num: cliente.telefone_2 },
    { label: 'Parente 2 / Recado', num: cliente.telefone_3 }
  ].filter(t => t.num && t.num.trim());

  if (disponiveis.length === 0) {
    showToast("Cliente não possui nenhum telefone cadastrado.", "danger");
    return;
  }

  // Se houver apenas 1 telefone, envia diretamente
  if (disponiveis.length === 1) {
    enviarMensagemWhatsApp(cliente.nome, disponiveis[0].num, parcelaNumero, parcelaValor, parcelaVencimento, isVencida, modalidade, totalParcelas, valorPrincipal);
    return;
  }

  // Se houver múltiplos telefones, exibe o modal para escolha
  const listaContainer = document.getElementById('lista-telefones-cobranca');
  listaContainer.innerHTML = '';

  disponiveis.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'btn btn-secondary';
    btn.style.width = '100%';
    btn.style.display = 'flex';
    btn.style.justify = 'space-between';
    btn.style.alignItems = 'center';
    btn.style.padding = '0.75rem 1rem';
    btn.innerHTML = `
      <span><strong>${t.label}:</strong> ${t.num}</span>
      <span class="badge badge-success">📱 Enviar Whats</span>
    `;
    btn.onclick = () => {
      closeModal('modal-selecionar-telefone');
      enviarMensagemWhatsApp(cliente.nome, t.num, parcelaNumero, parcelaValor, parcelaVencimento, isVencida, modalidade, totalParcelas, valorPrincipal);
    };
    listaContainer.appendChild(btn);
  });

  openModal('modal-selecionar-telefone');
}

function enviarMensagemWhatsApp(clienteNome, clienteTelefone, parcelaNumero, parcelaValor, parcelaVencimento, isVencida, modalidade, totalParcelas, valorPrincipal) {
  let cleanPhone = cleanPhoneNumber(clienteTelefone);
  if (!cleanPhone) {
    showToast("Telefone inválido.", "danger");
    return;
  }

  if (cleanPhone.length === 10 || cleanPhone.length === 11) {
    cleanPhone = '55' + cleanPhone;
  }

  const valorFormatado = formatCurrency(parcelaValor);
  const dataVencimentoFormatada = formatDate(parcelaVencimento);
  const isUltima = (parcelaNumero === totalParcelas) && (modalidade === 'juros_final');
  const isJurosFinal = modalidade === 'juros_final';

  let mensagem = '';

  if (isJurosFinal) {
    if (isVencida) {
      if (isUltima) {
        mensagem = `Olá ${clienteNome}! A parcela final nº ${parcelaNumero} do seu empréstimo, no valor de ${valorFormatado} (referente aos juros do mês + devolução integral do capital de ${formatCurrency(valorPrincipal)}), encontra-se *vencida* desde ${dataVencimentoFormatada}. Pedimos a gentileza de entrar em contato para regularização. Obrigado!`;
      } else {
        mensagem = `Olá ${clienteNome}! A parcela nº ${parcelaNumero} do seu empréstimo, referente apenas aos *juros mensais*, no valor de ${valorFormatado} (vencida em ${dataVencimentoFormatada}), encontra-se pendente. Solicitamos a regularização o mais breve possível. Obrigado!`;
      }
    } else {
      if (isUltima) {
        mensagem = `Olá ${clienteNome}! Lembrete: a *parcela final* nº ${parcelaNumero} do seu empréstimo vence em ${dataVencimentoFormatada}. O valor é ${valorFormatado}, que inclui os juros do mês + a devolução integral do capital de ${formatCurrency(valorPrincipal)}. Qualquer dúvida, estamos à disposição!`;
      } else {
        mensagem = `Olá ${clienteNome}! Lembrete amigável: a parcela nº ${parcelaNumero} do seu empréstimo (referente apenas aos *juros mensais*), no valor de ${valorFormatado}, vence em ${dataVencimentoFormatada}. Lembramos que o capital principal será quitado na parcela final. Qualquer dúvida, estamos à disposição!`;
      }
    }
  } else {
    if (isVencida) {
      mensagem = `Olá ${clienteNome}! Constatamos que a parcela nº ${parcelaNumero} do seu empréstimo, no valor de ${valorFormatado} (vencida em ${dataVencimentoFormatada}), encontra-se pendente. Solicitamos a gentileza de realizar o pagamento ou entrar em contato para regularização. Obrigado!`;
    } else {
      mensagem = `Olá ${clienteNome}! Lembrete amigável: a parcela nº ${parcelaNumero} do seu empréstimo, no valor de ${valorFormatado}, vence no dia ${dataVencimentoFormatada}. Qualquer dúvida, estamos à disposição!`;
    }
  }

  const url = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(mensagem)}`;
  window.open(url, '_blank');
}

// ---------------------------------------------------------------------------
// Pagamento de Parcelas (Pix, Dinheiro, Cartão Crédito/Débito)
// ---------------------------------------------------------------------------
function abrirModalBaixarPagamento(emprestimoId, parcelaId, valor) {
  document.getElementById('pay-emprestimo-id').value = emprestimoId;
  document.getElementById('pay-parcela-id').value = parcelaId;
  document.getElementById('pay-modal-valor').innerText = formatCurrency(valor);
  document.getElementById('pay-valor-pago').value = valor;
  document.getElementById('pay-observacao').value = '';
  document.getElementById('pay-metodo-select').value = 'pix';
  openModal('modal-baixar-pagamento');
}

async function handleConfirmarPagamentoParcela(e) {
  e.preventDefault();
  const emprestimoId = document.getElementById('pay-emprestimo-id').value;
  const parcelaId = document.getElementById('pay-parcela-id').value;
  const valorPago = parseFloat(document.getElementById('pay-valor-pago').value);
  const metodoPagamento = document.getElementById('pay-metodo-select').value;
  const observacao = document.getElementById('pay-observacao').value.trim() || null;

  try {
    const res = await fetchWithAuth(`${API_BASE}/emprestimos/${emprestimoId}/parcelas/${parcelaId}/pagar`, {
      method: 'POST',
      body: JSON.stringify({
        valor_pago: valorPago,
        metodo_pagamento: metodoPagamento,
        observacao: observacao
      })
    });

    if (!res) return;

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Erro ao registrar pagamento");
    }

    closeModal('modal-baixar-pagamento');
    showToast("Pagamento da parcela baixado com sucesso!");
    await verCarneEmprestimo(emprestimoId);
    await loadEmprestimos();
    await loadDashboard();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// Cartão de Crédito / Débito & Assinatura (Integração Asaas Gateway)
// ---------------------------------------------------------------------------
let activePixKey = "071757ec-7102-47f9-b8ee-242f4fbcc134";

function copiarChavePix(customText = null) {
  const pixKey = customText || activePixKey || "071757ec-7102-47f9-b8ee-242f4fbcc134";
  const btnText = document.getElementById('pix-copy-text');
  
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(pixKey).then(() => {
      showToast("Chave PIX copiada para a área de transferência!");
      if (btnText) btnText.innerText = "✅ Copiado!";
      setTimeout(() => { if (btnText) btnText.innerText = "Copiar Chave PIX"; }, 3000);
    }).catch(() => {
      fallbackCopiarChavePix(pixKey);
    });
  } else {
    fallbackCopiarChavePix(pixKey);
  }
}

function fallbackCopiarChavePix(text) {
  const tempInput = document.createElement("textarea");
  tempInput.value = text;
  document.body.appendChild(tempInput);
  tempInput.select();
  document.execCommand("copy");
  document.body.removeChild(tempInput);
  showToast("Chave PIX copiada com sucesso!");
  const btnText = document.getElementById('pix-copy-text');
  if (btnText) btnText.innerText = "✅ Copiado!";
  setTimeout(() => { if (btnText) btnText.innerText = "Copiar Chave PIX"; }, 3000);
}

async function gerarCobrancaPixAssinatura() {
  const container = document.getElementById('pix-cobranca-dinamica');
  if (!container) return;

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.2rem; gap: 0.6rem;">
      <div style="font-size: 0.88rem; color: #a5b4fc;">⏳ Conectando ao Asaas API para gerar Pix...</div>
    </div>
  `;

  try {
    const res = await fetchWithAuth(`${API_BASE}/pagamentos/pix/gerar-cobranca`, {
      method: 'POST'
    });

    if (!res) return;
    if (!res.ok) throw new Error("Falha ao gerar cobrança Pix no Asaas.");

    const data = await res.json();
    activePixKey = data.pix_copia_e_cola || data.chave_estatica || "071757ec-7102-47f9-b8ee-242f4fbcc134";

    let html = `<div style="background: rgba(30, 41, 59, 0.85); padding: 1.25rem; border-radius: 10px; border: 1px solid var(--border-color); text-align: center;">`;

    if (data.encoded_image) {
      html += `
        <div style="margin-bottom: 0.75rem;">
          <img src="data:image/png;base64,${data.encoded_image}" alt="QR Code Pix Asaas" style="max-width: 180px; width: 100%; border-radius: 8px; border: 2px solid var(--primary); background: #ffffff; padding: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
        </div>
      `;
    }

    html += `
      <div style="font-size: 0.82rem; color: #cbd5e1; margin-bottom: 0.5rem;">
        Valor da Assinatura: <strong style="color: #6ee7b7; font-size: 1.1rem;">R$ ${data.valor ? data.valor.toFixed(2).replace('.', ',') : '50,00'}</strong>
      </div>
      <div style="background: rgba(15, 23, 42, 0.95); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 1rem; text-align: left;">
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; font-weight: 600;">Chave / Copia e Cola PIX (Asaas):</div>
        <code id="pix-key-value" style="font-size: 0.85rem; color: var(--primary); font-weight: 700; word-break: break-all; display: block; background: rgba(0,0,0,0.2); padding: 6px 8px; border-radius: 4px;">${activePixKey}</code>
      </div>
      <button type="button" class="btn btn-primary" onclick="copiarChavePix('${activePixKey}')" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem; font-weight: 600; padding: 0.75rem;">
        📋 <span id="pix-copy-text">Copiar Chave PIX</span>
      </button>
    </div>`;

    container.innerHTML = html;
  } catch (err) {
    activePixKey = "071757ec-7102-47f9-b8ee-242f4fbcc134";
    container.innerHTML = `
      <div style="background: rgba(30, 41, 59, 0.85); padding: 1.25rem; border-radius: 10px; border: 1px solid var(--border-color); text-align: center;">
        <div style="font-size: 0.82rem; color: #f59e0b; margin-bottom: 0.5rem;">Chave PIX Direta (Asaas / E-mail):</div>
        <div style="background: rgba(15, 23, 42, 0.95); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 1rem; text-align: left;">
          <code id="pix-key-value" style="font-size: 0.9rem; color: var(--primary); font-weight: 700; word-break: break-all; display: block;">${activePixKey}</code>
        </div>
        <button type="button" class="btn btn-primary" onclick="copiarChavePix('${activePixKey}')" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.5rem; font-weight: 600; padding: 0.75rem;">
          📋 <span id="pix-copy-text">Copiar Chave PIX</span>
        </button>
      </div>
    `;
    showToast(err.message || "Erro ao conectar com Asaas. Usando Chave PIX direta.", "warning");
  }
}

function switchPayTab(tab) {
  const pixContent = document.getElementById('pay-content-pix');
  const cardContent = document.getElementById('pay-content-card');
  const tabPix = document.getElementById('tab-btn-pay-pix');
  const tabCard = document.getElementById('tab-btn-pay-card');

  if (tab === 'card') {
    pixContent.style.display = 'none';
    cardContent.style.display = 'block';
    tabPix.style.borderColor = 'transparent';
    tabPix.style.color = '#94a3b8';
    tabCard.style.borderColor = 'var(--primary)';
    tabCard.style.color = '#fff';
  } else {
    cardContent.style.display = 'none';
    pixContent.style.display = 'block';
    tabCard.style.borderColor = 'transparent';
    tabCard.style.color = '#94a3b8';
    tabPix.style.borderColor = 'var(--primary)';
    tabPix.style.color = '#fff';
  }
}

function formatarNumeroCartao(input) {
  let val = input.value.replace(/\D/g, '');
  if (val.length > 16) val = val.substring(0, 16);

  // Formatar em grupos de 4 dígitos
  const formatted = val.replace(/(\d{4})(?=\d)/g, '$1 ');
  input.value = formatted;

  // Detectar bandeira em tempo real
  const badge = document.getElementById('card-brand-badge');
  if (badge) {
    if (val.startsWith('4')) {
      badge.innerText = '💳 VISA';
    } else if (/^(5[1-5]|2[2-7])/.test(val)) {
      badge.innerText = '💳 MASTERCARD';
    } else if (/^(4011|4389|4514|4576|5041|5067|5090|6277|6362|6363)/.test(val)) {
      badge.innerText = '💳 ELO';
    } else if (/^(38|60)/.test(val)) {
      badge.innerText = '💳 HIPERCARD';
    } else {
      badge.innerText = val.length > 0 ? '💳 CARTÃO' : '';
    }
  }
}

function formatarValidadeCartao(input) {
  let val = input.value.replace(/\D/g, '');
  if (val.length >= 3) {
    input.value = val.substring(0, 2) + '/' + val.substring(2, 4);
  } else {
    input.value = val;
  }
}

async function handlePagamentoCartaoAssinatura(e) {
  e.preventDefault();
  const alertEl = document.getElementById('card-pay-alert');
  const btnSubmit = document.getElementById('btn-submit-cartao');

  if (alertEl) alertEl.style.display = 'none';

  const tipoCartao = document.getElementById('card-tipo').value;
  const numeroCartao = document.getElementById('card-numero').value.trim();
  const nomeTitular = document.getElementById('card-nome').value.trim();
  const validade = document.getElementById('card-validade').value.trim();
  const cvv = document.getElementById('card-cvv').value.trim();

  const numeroLimpo = numeroCartao.replace(/\D/g, '');
  if (!numeroLimpo || numeroLimpo.length < 13 || numeroLimpo.length > 19) {
    if (alertEl) {
      alertEl.innerText = "Número do cartão inválido. Por favor, insira todos os dígitos.";
      alertEl.style.display = 'block';
    }
    return;
  }

  if (!nomeTitular || nomeTitular.length < 2) {
    if (alertEl) {
      alertEl.innerText = "Nome do titular do cartão é obrigatório.";
      alertEl.style.display = 'block';
    }
    return;
  }

  if (!validade || !validade.includes('/') || validade.length < 5) {
    if (alertEl) {
      alertEl.innerText = "Validade do cartão inválida. Utilize o formato MM/AA.";
      alertEl.style.display = 'block';
    }
    return;
  }

  const cvvLimpo = cvv.replace(/\D/g, '');
  if (!cvvLimpo || cvvLimpo.length < 3 || cvvLimpo.length > 4) {
    if (alertEl) {
      alertEl.innerText = "Código de segurança (CVV) inválido.";
      alertEl.style.display = 'block';
    }
    return;
  }

  btnSubmit.disabled = true;
  btnSubmit.innerText = "⏳ Processando no Asaas Gateway...";

  try {
    const res = await fetchWithAuth(`${API_BASE}/pagamentos/cartao/assinar`, {
      method: 'POST',
      body: JSON.stringify({
        tipo_cartao: tipoCartao,
        numero_cartao: numeroLimpo,
        nome_titular: nomeTitular,
        validade: validade,
        cvv: cvvLimpo
      })
    });

    if (!res) return;

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Erro ao processar pagamento com cartão de crédito.");
    }

    const data = await res.json();
    showToast(data.mensagem, 'success');

    // Atualizar dados do usuário no localStorage
    const user = getUser();
    if (user) {
      user.status_assinatura = 'ativo';
      saveUser(user);
    }
    updateUserDisplay();

    closeModal('modal-upgrade');
    await loadDashboard();
    await loadClientes();

    alert(`🎉 PAGAMENTO APROVADO COM SUCESSO!\n\nTransação Asaas: ${data.gateway_tx_id}\nAutorização: ${data.codigo_autorizacao}\nBandeira: ${data.bandeira}\nStatus Assinatura: ATIVO\n\nSua conta foi ativada com acesso ilimitado!`);

  } catch (err) {
    if (alertEl) {
      alertEl.innerText = err.message;
      alertEl.style.display = 'block';
    } else {
      showToast(err.message, 'danger');
    }
  } finally {
    btnSubmit.disabled = false;
    btnSubmit.innerText = "🔒 Pagar R$ 50,00 e Ativar Agora";
  }
}

// ---------------------------------------------------------------------------
// API Calls - Administrador
// ---------------------------------------------------------------------------
async function loadAdminUsuarios() {
  try {
    const res = await fetchWithAuth(`${API_BASE}/admin/usuarios`);
    if (!res) return;
    const usuarios = await res.json();
    renderAdminUsuariosTable(usuarios);
  } catch (err) {
    showToast("Erro ao carregar lista de usuários do painel admin", "danger");
  }
}

function renderAdminUsuariosTable(usuarios) {
  const tbody = document.getElementById('tbody-admin-usuarios');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (usuarios.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted);">Nenhum usuário encontrado.</td></tr>`;
    return;
  }

  usuarios.forEach(u => {
    let badgeClass = 'badge-warning';
    let badgeLabel = 'TRIAL (TESTE)';
    if (u.status_assinatura === 'ativo') {
      badgeClass = 'badge-success';
      badgeLabel = 'ATIVO (ASSINANTE)';
    } else if (u.status_assinatura === 'bloqueado') {
      badgeClass = 'badge-danger';
      badgeLabel = 'BLOQUEADO';
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${u.id}</strong> ${u.is_admin ? '<span title="Admin Master">👑</span>' : ''}</td>
      <td>${u.nome}</td>
      <td>${u.email}</td>
      <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
      <td>${u.total_clientes} / 2</td>
      <td>${u.total_emprestimos}</td>
      <td>${formatDate(u.criado_em)}</td>
      <td class="text-right" style="display: flex; justify-content: flex-end; gap: 0.4rem;">
        ${u.status_assinatura !== 'ativo' ? `
          <button class="btn btn-primary btn-sm" onclick="alterarStatusAdmin(${u.id}, 'ativo')">✅ Ativar Plano</button>
        ` : ''}
        ${u.status_assinatura !== 'bloqueado' ? `
          <button class="btn btn-danger btn-sm" onclick="alterarStatusAdmin(${u.id}, 'bloqueado')">🚫 Bloquear</button>
        ` : ''}
        ${u.status_assinatura !== 'trial' ? `
          <button class="btn btn-secondary btn-sm" onclick="alterarStatusAdmin(${u.id}, 'trial')">🔄 Reset Trial</button>
        ` : ''}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function alterarStatusAdmin(usuarioId, novoStatus) {
  const acao = novoStatus === 'ativo' ? 'ativar a assinatura de' : novoStatus === 'bloqueado' ? 'bloquear' : 'resetar para trial';
  if (!confirm(`Tem certeza que deseja ${acao} este usuário?`)) return;

  try {
    const res = await fetchWithAuth(`${API_BASE}/admin/usuarios/${usuarioId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status_assinatura: novoStatus })
    });

    if (!res) return;
    if (!res.ok) throw new Error("Falha ao alterar status do usuário");

    showToast("Status de assinatura atualizado com sucesso!");
    await loadAdminUsuarios();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// ---------------------------------------------------------------------------
// Modal Helpers
// ---------------------------------------------------------------------------
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
  if (id === 'modal-upgrade') {
    switchPayTab('pix');
    gerarCobrancaPixAssinatura();
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

function openNovoEmprestimoModal(clienteId = null) {
  if (clienteId) {
    const select = document.getElementById('emp-cliente-select');
    if (select) select.value = clienteId;
  }
  const infoBox = document.getElementById('info-juros-final');
  if (infoBox) infoBox.style.display = 'none';
  const selectMod = document.getElementById('emp-modalidade-select');
  if (selectMod) selectMod.value = 'price';
  openModal('modal-novo-emprestimo');
}

function imprimirCarne() {
  window.print();
}
