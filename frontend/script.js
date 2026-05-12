/**
 * script.js — ComprasCorp v3
 * Catálogo clicável → busca automática no Mercado Livre → painel de resultados
 */

"use strict";

const API_BASE = "http://localhost:8000";

// ── Estado ────────────────────────────────────────────────────────────────────
const state = {
  catalogo: [],
  catalogoFiltrado: [],
  allResults: [],
  filteredResults: [],
  sortColumn: "preco",
  sortDirection: "asc",
  searchQuery: "",
  deletePendingId: null,
  activeItemId: null,
  activeMasterCatalog: null,
  activeDirectory: null,
};

// ── DOM ───────────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const els = {
  // Header
  logoLink:        $("logo-link"),
  btnAbrirModal:   $("btn-abrir-modal"),

  // Catálogo
  catalogSearch:   $("catalog-search"),
  catalogCount:    $("catalog-count"),
  catalogNav:      $("catalog-nav"),
  btnBackCatalogs: $("btn-back-catalogs"),
  breadcrumbContainer: $("breadcrumb-container"),
  activeCatalogTitle: $("active-catalog-title"),
  catalogGrid:     $("catalog-grid"),
  emptyCatalog:    $("empty-catalog"),
  
  // Header Stats
  statItems:       $("stat-items"),
  statPhotos:      $("stat-photos"),
  statDepts:       $("stat-depts"),

  // Painel resultados
  resultsPanel:    $("results-panel"),
  panelItemIcon:   $("panel-item-icon"),
  panelItemNome:   $("panel-item-nome"),
  panelItemCat:    $("panel-item-cat"),
  resultsCount:    $("results-count"),
  btnExport:       $("btn-export"),
  btnFecharPainel: $("btn-fechar-painel"),
  pstatTotal:      $("pstat-total"),
  pstatMenor:      $("pstat-menor"),
  pstatMaior:      $("pstat-maior"),
  pstatMedia:      $("pstat-media"),
  searchInput:     $("search-input"),
  sortSelect:      $("sort-select"),
  resultCards:     $("result-cards"),

  // Loading
  loadingOverlay:  $("loading-overlay"),
  loadingText:     $("loading-text"),
  loadingStep:     $("loading-step"),

  // Modal adicionar
  modalOverlay:    $("modal-overlay"),
  modalClose:      $("modal-close"),
  modalCancel:     $("modal-cancel"),
  formNovoItem:    $("form-novo-item"),
  novoNome:        $("novo-nome"),
  novoCategoria:   $("novo-categoria"),
  novoIcone:       $("novo-icone"),
  erroNome:        $("erro-nome"),
  btnSalvarItem:   $("btn-salvar-item"),

  // Modal remover
  modalDelOverlay: $("modal-del-overlay"),
  modalDelDesc:    $("modal-del-desc"),
  modalDelCancel:  $("modal-del-cancel"),
  modalDelConfirm: $("modal-del-confirm"),

  // Modal Detalhes (Novo)
  modalDetailsOverlay: $("modal-details-overlay"),
  modalDetailsClose:   $("modal-details-close"),
  modalDetailsOk:      $("modal-details-ok"),
  detailsIcon:         $("details-icon"),
  detailsTitle:        $("details-title"),
  detailsCat:          $("details-cat"),
  detailsPhoto:        $("details-photo"),
  detailsPrice:        $("details-price"),
  detailsModel:        $("details-model"),
  detailsColor:        $("details-color"),
  btnEditPhoto:        $("btn-edit-photo"),

  toastContainer:  $("toast-container"),
};

// ── Utilitários ───────────────────────────────────────────────────────────────

function formatCurrency(v) {
  if (v == null || isNaN(v)) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);
}

function escapeHtml(text) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text ?? "")));
  return d.innerHTML;
}

/**
 * Limpa nomes de produtos vindos do banco que carregam especificações técnicas.
 * Ex: "HEAD SET JABRA HEADSET;POTENCIA MAXIMA:10 MILI W;..." → "Head Set Jabra Headset"
 * Regras: pega apenas o trecho antes do 1º ";", limita a 5 palavras e aplica Title Case.
 */
function cleanItemName(nome) {
  if (!nome) return nome;
  // Remove tudo a partir do primeiro ponto-e-vírgula (specs técnicas)
  const firstPart = nome.split(';')[0].trim();
  // Limita a 5 palavras e converte para Title Case
  return firstPart
    .split(/\s+/)
    .slice(0, 5)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function showToast(msg, type = "info", dur = 4000) {
  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || "ℹ️"}</span><span>${msg}</span>`;
  els.toastContainer.appendChild(t);
  setTimeout(() => { t.classList.add("hiding"); setTimeout(() => t.remove(), 300); }, dur);
}

function animateNumber(el, target, format = (v) => v.toFixed(0)) {
  const dur = 600, start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / dur, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = format(e * target);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Loading ───────────────────────────────────────────────────────────────────

const loadingSteps = [
  "🔍 Consultando Mercado Livre...",
  "🛒 Comparando ofertas disponíveis...",
  "📊 Ordenando por melhor preço...",
  "✅ Finalizando análise...",
];
let loadingIdx = 0, loadingTimer = null;

function showLoading(itemNome) {
  els.loadingText.textContent = `Buscando opções de ${itemNome}...`;
  loadingIdx = 0;
  els.loadingStep.textContent = loadingSteps[0];
  els.loadingOverlay.classList.add("active");
  loadingTimer = setInterval(() => {
    loadingIdx = (loadingIdx + 1) % loadingSteps.length;
    els.loadingStep.textContent = loadingSteps[loadingIdx];
  }, 1800);
}

function hideLoading() {
  clearInterval(loadingTimer);
  els.loadingOverlay.classList.remove("active");
}

// ── Modais ────────────────────────────────────────────────────────────────────

function openModal() {
  els.formNovoItem.reset();
  els.erroNome.textContent = "";
  els.erroNome.classList.remove("visible");
  els.novoNome.classList.remove("invalid");
  els.modalOverlay.classList.add("active");
  setTimeout(() => els.novoNome.focus(), 100);
}

function closeModal() {
  els.modalOverlay.classList.remove("active");
}

els.btnAbrirModal.addEventListener("click", openModal);
els.modalClose.addEventListener("click", closeModal);
els.modalCancel.addEventListener("click", closeModal);
els.modalOverlay.addEventListener("click", (e) => { if (e.target === els.modalOverlay) closeModal(); });

function openDelModal(item) {
  state.deletePendingId = item.id;
  els.modalDelDesc.textContent = `Deseja remover "${item.nome}" do catálogo?`;
  els.modalDelOverlay.classList.add("active");
}

function closeDelModal() {
  els.modalDelOverlay.classList.remove("active");
  state.deletePendingId = null;
}

els.modalDelCancel.addEventListener("click", closeDelModal);
els.modalDelOverlay.addEventListener("click", (e) => { if (e.target === els.modalDelOverlay) closeDelModal(); });
els.modalDelConfirm.addEventListener("click", async () => {
  if (!state.deletePendingId) return;
  await removerItem(state.deletePendingId);
  closeDelModal();
});

// ── Modal Detalhes ────────────────────────────────────────────────────────────

function openDetailsModal(detalhes) {
  state.currentDetailsId = detalhes.item_id;
  els.detailsIcon.textContent = detalhes.item_icone || "📦";
  els.detailsTitle.textContent = cleanItemName(detalhes.item_nome) || "Produto";
  els.detailsCat.textContent = detalhes.item_categoria || "";
  
  els.detailsPhoto.src = detalhes.foto || "";
  
  els.detailsPrice.textContent = formatCurrency(detalhes.ultimo_preco);
  els.detailsModel.textContent = detalhes.modelo || "Padrão";
  els.detailsColor.textContent = detalhes.cor || "Indefinida";

  els.modalDetailsOverlay.classList.add("active");
}

function closeDetailsModal() {
  els.modalDetailsOverlay.classList.remove("active");
  state.activeItemId = null;
  document.querySelectorAll(".catalog-card").forEach(c => c.classList.remove("active"));
}

els.modalDetailsClose.addEventListener("click", closeDetailsModal);
els.modalDetailsOk.addEventListener("click", closeDetailsModal);
els.modalDetailsOverlay.addEventListener("click", (e) => { 
  if (e.target === els.modalDetailsOverlay) closeDetailsModal(); 
});

if (els.btnEditPhoto) {
    els.btnEditPhoto.addEventListener("click", async () => {
        if (!state.currentDetailsId) return;
        const url = prompt("Cole a URL da foto (JPG/PNG/WEBP) para sobrepor a busca automática:");
        if (!url) return;
        
        try {
            const res = await fetch(`${API_BASE}/api/catalogo/${state.currentDetailsId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ foto: url })
            });
            if (!res.ok) throw new Error("Falha ao salvar foto.");
            els.detailsPhoto.src = url;
            showToast("Foto atualizada com sucesso no servidor!", "success");
            
            // Atualiza memória local para busca rápida
            const item = state.catalogo.find(i => i.id === state.currentDetailsId);
            if (item) item.foto = url;
        } catch(e) {
            showToast(e.message, "error");
        }
    });
}


// ── Formulário Adicionar ──────────────────────────────────────────────────────

els.formNovoItem.addEventListener("submit", async (e) => {
  e.preventDefault();

  const nome = els.novoNome.value.trim();
  if (!nome) {
    els.novoNome.classList.add("invalid");
    els.erroNome.textContent = "Informe o nome do produto.";
    els.erroNome.classList.add("visible");
    return;
  }

  els.btnSalvarItem.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/catalogo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome,
        categoria: els.novoCategoria.value.trim() || "Geral",
        icone: els.novoIcone.value.trim() || "📦",
      }),
    });

    if (!res.ok) throw new Error("Erro ao adicionar item.");

    showToast(`"${nome}" adicionado ao catálogo!`, "success");
    closeModal();
    await loadCatalogo();

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    els.btnSalvarItem.disabled = false;
  }
});

// ── Carregar e Renderizar Catálogo ────────────────────────────────────────────

async function loadCatalogo() {
  try {
    const res = await fetch(`${API_BASE}/api/catalogo`);
    if (!res.ok) throw new Error("Erro ao carregar catálogo.");
    state.catalogo = await res.json();
    state.catalogoFiltrado = [...state.catalogo];
    updateHeaderStats(state.catalogo);
    renderCatalogo();
  } catch (err) {
    showToast("Erro ao carregar catálogo.", "error");
  }
}

function updateHeaderStats(items) {
  if (!els.statItems) return;
  const total = items.length;
  const withPhoto = items.filter(i => i.foto).length;
  
  const masterObj = {};
  items.forEach(item => {
    const cat = item.categoria || "Geral";
    const master = getMasterCatalog(cat);
    masterObj[master] = true;
  });
  const depts = Object.keys(masterObj).length;

  els.statItems.textContent = `📦 ${total} itens`;
  els.statPhotos.textContent = `🖼️ ${withPhoto} fotos`;
  els.statDepts.textContent = `📂 ${depts} deptos`;
}

function getMasterCatalog(catStr) {
    const c = catStr.toLowerCase();
    
    if (c.includes('mouse') || c.includes('teclado') || c.includes('headset') || c.includes('webcam') || c.includes('jabra') || c.includes('audio') || c.includes('fone')) {
        return "Acessórios e Periféricos";
    }
    if (c.includes('notebook') || c.includes('laptop') || c.includes('desktop') || c.includes('monitor') || c.includes('computador') || c.includes('informática') || c.includes('tablet')) {
        return "Informática";
    }
    if (c.includes('celular') || c.includes('telefone') || c.includes('smartphone') || c.includes('apple') || c.includes('sams') || c.includes('sarn') || c.includes('xiaomi') || c.includes('motorola')) {
        return "Telefonia e Mobile";
    }
    if (c.includes('roteador') || c.includes('wi-fi') || c.includes('antena') || c.includes('telecom') || c.includes('switch') || c.includes('rede') || c.includes('rj45') || c.includes('starlink')) {
        return "Redes e Telecom";
    }
    if (c.includes('bateria') || c.includes('nobreak') || c.includes('fonte') || c.includes('elétrica') || c.includes('carregador')) {
        return "Energia e Baterias";
    }
    if (c.includes('pendrive') || c.includes('ssd') || c.includes('hd') || c.includes('memória') || c.includes('processador')) {
        return "Armazenamento & Hardware";
    }
    if (c.includes('cabo') || c.includes('conector') || c.includes('adaptador') || c.includes('hub')) {
        return "Cabos e Conectividade";
    }
    if (c.includes('pelicula') || c.includes('capa') || c.includes('mochila') || c.includes('bag')) {
        return "Bolsas e Proteção";
    }
    if (c.includes('cadeira') || c.includes('mobiliário') || c.includes('mesa') || c.includes('escritório') || c.includes('arquivo')) {
        return "Mobiliário Corporativo";
    }
    if (c.includes('impressora') || c.includes('brother') || c.includes('epson') || c.includes('hp')) {
        return "Impressão e Imagem";
    }
    if (c.includes('coletor') || c.includes('leitor') || c.includes('gatilho')) {
        return "Automação e Scanners";
    }
    if (c.includes('durex') || c.includes('alcool') || c.includes('alicate') || c.includes('ferramenta') || c.includes('teste')) {
        return "Ferramentas e Manutenção";
    }
    if (c.includes('projetor') || c.includes('camera') || c.includes('tv') || c.includes('video')) {
        return "Áudio e Vídeo";
    }
    return "Outros / Diversos";
}

function getIconForMaster(master) {
    switch(master) {
        case "Informática": return "💻";
        case "Acessórios e Periféricos": return "⌨️";
        case "Telefonia e Mobile": return "📱";
        case "Redes e Telecom": return "📡";
        case "Energia e Baterias": return "🔋";
        case "Armazenamento & Hardware": return "💾";
        case "Cabos e Conectividade": return "🔌";
        case "Bolsas e Proteção": return "🛡️";
        case "Mobiliário Corporativo": return "🪑";
        case "Impressão e Imagem": return "🖨️";
        case "Automação e Scanners": return "📟";
        case "Ferramentas e Manutenção": return "🧰";
        case "Áudio e Vídeo": return "📽️";
        default: return "📦";
    }
}

function getIconForCategory(cat) {
    const c = cat.toLowerCase();
    
    if (c.includes('cabo')) return '🔌';
    if (c.includes('adaptador') || c.includes('hub') || c.includes('conector') || c.includes('emenda')) return '🔄';
    if (c.includes('notebook') || c.includes('laptop')) return '💻';
    if (c.includes('desktop') || c.includes('computador')) return '🖥️';
    if (c.includes('monitor') || c.includes('tela')) return '📺';
    if (c.includes('teclado')) return '⌨️';
    if (c.includes('mouse')) return '🖱️';
    if (c.includes('celular') || c.includes('telefone') || c.includes('smartphone') || c.includes('iphone')) return '📱';
    if (c.includes('tablet') || c.includes('ipad')) return '📟';
    if (c.includes('impressora') || c.includes('brother')) return '🖨️';
    if (c.includes('coletor') || c.includes('leitor') || c.includes('scanner')) return '📠';
    if (c.includes('gatilho')) return '🔫';
    if (c.includes('headset') || c.includes('fone') || c.includes('audio') || c.includes('jabra') || c.includes('espuma')) return '🎧';
    if (c.includes('cadeira') || c.includes('mobiliário')) return '🪑';
    if (c.includes('mesa') || c.includes('escritório')) return '🖥️';
    if (c.includes('bateria') || c.includes('pilha')) return '🔋';
    if (c.includes('nobreak') || c.includes('fonte') || c.includes('elétrica') || c.includes('carregador')) return '🔌';
    if (c.includes('roteador') || c.includes('wi-fi') || c.includes('antena') || c.includes('telecom') || c.includes('starlink')) return '📡';
    if (c.includes('switch') || c.includes('rede') || c.includes('rj45')) return '🖧';
    if (c.includes('pelicula') || c.includes('capa') || c.includes('capinha') || c.includes('bag') || c.includes('mochila')) return '🛡️';
    if (c.includes('pendrive') || c.includes('ssd') || c.includes('hd') || c.includes('memoria')) return '💾';
    if (c.includes('projetor') || c.includes('camera') || c.includes('webcam')) return '📽️';
    if (c.includes('apple') || c.includes('samsung') || c.includes('xiaomi') || c.includes('motorola')) return '📱';
    if (c.includes('alicate') || c.includes('teste') || c.includes('durex') || c.includes('ferramenta')) return '🛠️';
    if (c.includes('alcool') || c.includes('limpeza')) return '🧴';
    return '📦';
}

function updateBreadcrumb() {
  if (!els.breadcrumbContainer) return;
  if (!state.activeMasterCatalog) {
    els.breadcrumbContainer.innerHTML = '';
    return;
  }
  
  let html = `<span class="breadcrumb-item clickable" onclick="window.handleBackToRoot()">Departamentos</span>`;
  html += `<span class="breadcrumb-sep">›</span>`;
  
  if (!state.activeDirectory) {
    html += `<span class="breadcrumb-item current">${escapeHtml(state.activeMasterCatalog)}</span>`;
  } else {
    html += `<span class="breadcrumb-item clickable" onclick="window.handleBackToMaster()">${escapeHtml(state.activeMasterCatalog)}</span>`;
    html += `<span class="breadcrumb-sep">›</span>`;
    html += `<span class="breadcrumb-item current">${escapeHtml(cleanItemName(state.activeDirectory))}</span>`;
  }
  
  els.breadcrumbContainer.innerHTML = html;
}

window.handleBackToRoot = () => {
    state.activeMasterCatalog = null;
    state.activeDirectory = null;
    saveNavState();
    renderCatalogo();
};

window.handleBackToMaster = () => {
    state.activeDirectory = null;
    saveNavState();
    renderCatalogo();
};

function renderCatalogo() {
  const items = state.catalogoFiltrado;
  
  // GLOBAL SEARCH (BUSCA GLOBAL)
  if (state.pesquisa) {
      if (els.catalogNav) els.catalogNav.style.display = "none";
      els.catalogCount.textContent = `${items.length} item${items.length !== 1 ? 's' : ''} encontrados`;
      
      if (items.length === 0) {
        els.catalogGrid.style.display = "none";
        els.emptyCatalog.style.display = "flex";
        return;
      }
      
      els.catalogGrid.style.display = "block";
      els.emptyCatalog.style.display = "none";
      
      let html = `<div class="cat-items fade-in">`;
      items.forEach(item => {
        const active = item.id === state.activeItemId ? "active" : "";
        const icone = (item.icone === "📦" || !item.icone) ? getIconForCategory(item.categoria || "Geral") : item.icone;
        const fotoHtml = item.foto ? 
            `<div class="card-img-wrap"><img src="${escapeHtml(item.foto)}" class="card-img" alt="${escapeHtml(item.nome)}" loading="lazy"></div>` : 
            `<div class="card-icon" style="font-size: 32px; filter: drop-shadow(0 4px 10px rgba(59,130,246,0.2));">${escapeHtml(icone)}</div>`;
        const badgeHtml = `<div class="badge-photo-status" title="${item.foto ? 'Com foto' : 'Sem foto'}">${item.foto ? '🖼️' : '⚠️'}</div>`;
        
        html += `
          <div class="catalog-card ${active}" data-id="${escapeHtml(item.id)}" id="card-${escapeHtml(item.id)}" tabindex="0" role="button" aria-label="Buscar ${escapeHtml(item.nome)}">
            ${badgeHtml}
            <button class="card-del-btn" title="Remover do catálogo" onclick="event.stopPropagation(); window.handleDelItem('${escapeHtml(item.id)}')">✕</button>
            ${fotoHtml}
            <div class="card-nome" title="${escapeHtml(item.nome)}">${escapeHtml(cleanItemName(item.nome))}</div>
            <div class="card-cta">Ver detalhes →</div>
          </div>
        `;
      });
      html += `</div>`;
      els.catalogGrid.innerHTML = html;

      // Eventos de clique nos cards
      els.catalogGrid.querySelectorAll(".catalog-card").forEach(card => {
        card.addEventListener("click", () => buscarItem(card.dataset.id));
        card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") buscarItem(card.dataset.id); });
      });
      return;
  }
  
  if (state.activeMasterCatalog === null) {
      // NÍVEL 1: DEPARTAMENTOS MASTER
      if (els.catalogNav) els.catalogNav.style.display = "none";
      
      const masterObj = {};
      items.forEach(item => {
        const cat = item.categoria || "Geral";
        const master = getMasterCatalog(cat);
        
        if (!masterObj[master]) masterObj[master] = { name: master, count: 0, icon: getIconForMaster(master) };
        masterObj[master].count++;
      });
      const masters = Object.values(masterObj).sort((a,b) => a.name.localeCompare(b.name));
      
      els.catalogCount.textContent = `${masters.length} departamento${masters.length !== 1 ? 's' : ''}`;
      
      if (masters.length === 0) {
        els.catalogGrid.style.display = "none";
        els.emptyCatalog.style.display = "flex";
        return;
      }
      
      els.catalogGrid.style.display = "block";
      els.emptyCatalog.style.display = "none";
      
      let html = `<div class="cat-items fade-in">`;
      masters.forEach(m => {
        html += `
          <div class="catalog-card" tabindex="0" role="button" aria-label="Abrir departamento ${escapeHtml(m.name)}" onclick="window.openMasterCatalog('${escapeHtml(m.name).replace(/'/g, "\\'")}')">
            <div class="card-icon" style="font-size: 44px; margin-bottom: 12px; filter: drop-shadow(0 4px 10px rgba(255,255,255,0.1));">${escapeHtml(m.icon)}</div>
            <div class="card-nome" style="font-size: 15px;">${escapeHtml(m.name)}</div>
            <div class="card-cta" style="opacity: 0.7">${m.count} item${m.count !== 1 ? 's' : ''}</div>
          </div>
        `;
      });
      html += `</div>`;
      els.catalogGrid.innerHTML = html;

  } else if (state.activeDirectory === null) {
      // NÍVEL 2: SUB-CATÁLOGOS DENTRO DO DEPARTAMENTO
      if (els.catalogNav) els.catalogNav.style.display = "flex";
      updateBreadcrumb();
      if (els.btnBackCatalogs) els.btnBackCatalogs.textContent = "← Voltar aos Departamentos";
      
      const subObj = {};
      items.forEach(item => {
        const cat = item.categoria || "Geral";
        const master = getMasterCatalog(cat);
        if (master === state.activeMasterCatalog) {
            if (!subObj[cat]) subObj[cat] = { name: cat, count: 0, icon: getIconForCategory(cat) };
            subObj[cat].count++;
        }
      });
      const subcats = Object.values(subObj).sort((a,b) => a.name.localeCompare(b.name));
      
      els.catalogCount.textContent = `${subcats.length} catálogo${subcats.length !== 1 ? 's' : ''}`;
      
      els.catalogGrid.style.display = "block";
      els.emptyCatalog.style.display = "none";
      
      let html = `<div class="cat-items fade-in">`;
      subcats.forEach(cat => {
        const cleanName = cleanItemName(cat.name);
        html += `
          <div class="catalog-card" tabindex="0" role="button" aria-label="Abrir catálogo ${escapeHtml(cleanName)}" onclick="window.openDirectory('${escapeHtml(cat.name).replace(/'/g, "\\'")}')">
            <div class="card-icon" style="font-size: 38px; margin-bottom: 12px; filter: drop-shadow(0 4px 10px rgba(255,255,255,0.1));">${escapeHtml(cat.icon)}</div>
            <div class="card-nome" style="font-size: 14px;" title="${escapeHtml(cat.name)}">${escapeHtml(cleanName)}</div>
            <div class="card-cta" style="opacity: 0.7">${cat.count} item${cat.count !== 1 ? 's' : ''}</div>
          </div>
        `;
      });
      html += `</div>`;
      els.catalogGrid.innerHTML = html;
  
  } else {
      // NÍVEL 3: ITENS DENTRO DO SUB-CATÁLOGO
      if (els.catalogNav) els.catalogNav.style.display = "flex";
      updateBreadcrumb();
      if (els.btnBackCatalogs) els.btnBackCatalogs.textContent = "← Voltar aos Catálogos";
      
      const dirItems = items.filter(i => (i.categoria || "Geral") === state.activeDirectory && getMasterCatalog(i.categoria || "Geral") === state.activeMasterCatalog);
      
      els.catalogCount.textContent = `${dirItems.length} item${dirItems.length !== 1 ? 's' : ''}`;
      
      if (dirItems.length === 0) {
        els.catalogGrid.style.display = "none";
        els.emptyCatalog.style.display = "flex";
        return;
      }
      
      els.catalogGrid.style.display = "block";
      els.emptyCatalog.style.display = "none";
      
      let html = `<div class="cat-items fade-in">`;
      dirItems.forEach(item => {
        const active = item.id === state.activeItemId ? "active" : "";
        const icone = (item.icone === "📦" || !item.icone) ? getIconForCategory(item.categoria || "Geral") : item.icone;
        const fotoHtml = item.foto ? 
            `<div class="card-img-wrap"><img src="${escapeHtml(item.foto)}" class="card-img" alt="${escapeHtml(item.nome)}" loading="lazy"></div>` : 
            `<div class="card-icon" style="font-size: 32px; filter: drop-shadow(0 4px 10px rgba(59,130,246,0.2));">${escapeHtml(icone)}</div>`;
        const badgeHtml = `<div class="badge-photo-status" title="${item.foto ? 'Com foto' : 'Sem foto'}">${item.foto ? '🖼️' : '⚠️'}</div>`;
        
        html += `
          <div class="catalog-card ${active}" data-id="${escapeHtml(item.id)}" id="card-${escapeHtml(item.id)}" tabindex="0" role="button" aria-label="Buscar ${escapeHtml(item.nome)}">
            ${badgeHtml}
            <button class="card-del-btn" title="Remover do catálogo" onclick="event.stopPropagation(); window.handleDelItem('${escapeHtml(item.id)}')">✕</button>
            ${fotoHtml}
            <div class="card-nome" title="${escapeHtml(item.nome)}">${escapeHtml(cleanItemName(item.nome))}</div>
            <div class="card-cta">Ver detalhes →</div>
          </div>
        `;
      });
      html += `</div>`;
      els.catalogGrid.innerHTML = html;

      // Eventos de clique nos cards
      els.catalogGrid.querySelectorAll(".catalog-card").forEach(card => {
        card.addEventListener("click", () => buscarItem(card.dataset.id));
        card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") buscarItem(card.dataset.id); });
      });
  }
}

function saveNavState() {
  sessionStorage.setItem('compras_master', state.activeMasterCatalog || '');
  sessionStorage.setItem('compras_dir', state.activeDirectory || '');
}

window.openMasterCatalog = (name) => {
  state.activeMasterCatalog = name;
  state.activeDirectory = null;
  state.pesquisa = ""; 
  els.catalogSearch.value = "";
  state.catalogoFiltrado = [...state.catalogo];
  saveNavState();
  renderCatalogo();
};

window.openDirectory = (dirName) => {
  state.activeDirectory = dirName;
  state.pesquisa = ""; 
  els.catalogSearch.value = "";
  state.catalogoFiltrado = [...state.catalogo];
  saveNavState();
  renderCatalogo();
};

window.handleBack = () => {
    if (state.activeDirectory !== null) {
        state.activeDirectory = null;
    } else if (state.activeMasterCatalog !== null) {
        state.activeMasterCatalog = null;
    }
    state.pesquisa = "";
    els.catalogSearch.value = "";
    state.catalogoFiltrado = [...state.catalogo];
    saveNavState();
    renderCatalogo();
};

if (els.btnBackCatalogs) {
  els.btnBackCatalogs.addEventListener("click", window.handleBack);
}

// Filtro do catálogo
els.catalogSearch.addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  state.pesquisa = q;
  state.catalogoFiltrado = q
    ? state.catalogo.filter(i => i.nome.toLowerCase().includes(q) || (i.categoria || "").toLowerCase().includes(q))
    : [...state.catalogo];
  renderCatalogo();
});

// ── Remover Item do Catálogo ──────────────────────────────────────────────────

async function removerItem(id) {
  try {
    const res = await fetch(`${API_BASE}/api/catalogo/${id}`, { method: "DELETE" });
    if (!res.ok && res.status !== 204) throw new Error("Erro ao remover.");
    showToast("Item removido do catálogo.", "info");
    if (state.activeItemId === id) fecharPainel();
    await loadCatalogo();
  } catch (err) {
    showToast(err.message, "error");
  }
}

window.handleDelItem = (id) => {
  const item = state.catalogo.find(i => i.id === id);
  if (item) openDelModal(item);
};

// ── Buscar Item ───────────────────────────────────────────────────────────────

async function buscarItem(itemId) {
  const item = state.catalogo.find(i => i.id === itemId);
  if (!item) return;

  state.activeItemId = itemId;

  // Destaca card ativo
  document.querySelectorAll(".catalog-card").forEach(c => c.classList.remove("active"));
  const activeCard = document.getElementById(`card-${itemId}`);
  if (activeCard) activeCard.classList.add("active");

  showLoading(item.nome);

  try {
    const res = await fetch(`${API_BASE}/api/buscar/${itemId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
      throw new Error(err.detail || `Erro ${res.status}`);
    }
    const data = await res.json();
    hideLoading();
    
    fecharPainel(); // Oculte o painel se estiver aberto
    openDetailsModal(data.detalhes);

  } catch (err) {
    hideLoading();
    showToast(err.message || "Erro na busca.", "error", 6000);
  }
}

// ── Painel de Resultados ──────────────────────────────────────────────────────

function processResults(resultados) {
  state.allResults = resultados;
  state.filteredResults = [...resultados];
  updatePanelStats();
  renderResultCards(state.filteredResults);
}

function updatePanelStats() {
  const r = state.filteredResults;
  const count = r.length;
  const precos = r.map(x => x.preco).filter(p => p != null && !isNaN(p));
  const menor = precos.length ? Math.min(...precos) : null;
  const maior = precos.length ? Math.max(...precos) : null;
  const media = precos.length ? precos.reduce((a, b) => a + b, 0) / precos.length : null;

  animateNumber(els.pstatTotal, count);
  els.pstatMenor.textContent = menor != null ? formatCurrency(menor) : "—";
  els.pstatMaior.textContent = maior != null ? formatCurrency(maior) : "—";
  els.pstatMedia.textContent = media != null ? formatCurrency(media) : "—";
  els.resultsCount.textContent = `${count} opção${count !== 1 ? "ões" : ""}`;
}

function getPrazoBadge(prazo) {
  if (!prazo || prazo === "Consultar no site" || prazo === "Consultar") {
    return `<span class="prazo-badge consultar">🔍 Consultar</span>`;
  }
  if (["full", "1-2", "express"].some(k => prazo.toLowerCase().includes(k))) {
    return `<span class="prazo-badge rapido">⚡ ${escapeHtml(prazo)}</span>`;
  }
  return `<span class="prazo-badge normal">🚚 ${escapeHtml(prazo)}</span>`;
}

function renderResultCards(results) {
  if (results.length === 0) {
    els.resultCards.innerHTML = `
      <div class="empty-results">
        <div class="empty-icon">🔍</div>
        <div class="empty-title">Nenhum resultado encontrado</div>
        <div class="empty-sub">Tente remover o filtro ou busque novamente.</div>
      </div>
    `;
    return;
  }

  els.resultCards.innerHTML = results.map((item, i) => {
    const frete = item.frete_gratis
      ? `<span class="frete-gratis-badge">✓ Frete grátis</span>`
      : "";
    return `
      <div class="result-card" style="--delay: ${i * 0.04}s">
        <div class="result-card-inner">
          <div class="result-titulo" title="${escapeHtml(item.titulo || "")}">
            ${escapeHtml(item.titulo || "Produto sem título")}
          </div>
          <div class="result-footer">
            <div class="result-preco-wrap">
              <div class="result-preco">${formatCurrency(item.preco)}</div>
              ${frete}
            </div>
            <div class="result-meta">
              ${getPrazoBadge(item.prazo)}
              <span class="marketplace-badge ml">🛒 ML</span>
            </div>
            <a
              class="btn-ver"
              href="${escapeHtml(item.link || "#")}"
              target="_blank"
              rel="noopener noreferrer"
              onclick="if(!this.href||this.href==='${location.origin}/#'){event.preventDefault();showToastGlobal('Link não disponível.','info');}"
            >
              Ver oferta ↗
            </a>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

window.showToastGlobal = showToast;

// ── Filtro e ordenação dos resultados ─────────────────────────────────────────

els.searchInput.addEventListener("input", (e) => {
  state.searchQuery = e.target.value.toLowerCase().trim();
  applySort();
});

els.sortSelect.addEventListener("change", applySort);

function applySort() {
  const [col, dir] = els.sortSelect.value.split("-");
  let filtered = [...state.allResults];

  if (state.searchQuery) {
    filtered = filtered.filter(item =>
      [item.titulo, item.item_nome].join(" ").toLowerCase().includes(state.searchQuery)
    );
  }

  filtered.sort((a, b) => {
    let vA = a[col], vB = b[col];
    if (typeof vA === "string") vA = vA.toLowerCase();
    if (typeof vB === "string") vB = vB.toLowerCase();
    if (vA < vB) return dir === "asc" ? -1 : 1;
    if (vA > vB) return dir === "asc" ? 1 : -1;
    return 0;
  });

  state.filteredResults = filtered;
  updatePanelStats();
  renderResultCards(filtered);
}

// ── Fechar painel / logo ──────────────────────────────────────────────────────

function fecharPainel() {
  els.resultsPanel.classList.remove("visible");
  state.activeItemId = null;
  document.querySelectorAll(".catalog-card").forEach(c => c.classList.remove("active"));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

els.btnFecharPainel.addEventListener("click", fecharPainel);
els.logoLink.addEventListener("click", (e) => { e.preventDefault(); fecharPainel(); });

// ── Exportar Excel ────────────────────────────────────────────────────────────

els.btnExport.addEventListener("click", async () => {
  if (state.allResults.length === 0) { showToast("Nenhum resultado para exportar.", "info"); return; }
  els.btnExport.disabled = true;
  els.btnExport.innerHTML = "⏳ Gerando...";
  try {
    const res = await fetch(`${API_BASE}/api/export`);
    if (!res.ok) throw new Error("Erro ao gerar arquivo.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `compras_${Date.now()}.xlsx`;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    showToast("Excel exportado!", "success");
  } catch (err) {
    showToast("Erro: " + err.message, "error");
  } finally {
    els.btnExport.disabled = false;
    els.btnExport.innerHTML = `<span>📥</span> Exportar Excel`;
  }
});

// ── Auto-fotos ────────────────────────────────────────────────────────────────

const afEls = {
  overlay: $("modal-autofotos-overlay"),
  desc:    $("autofotos-desc"),
  current: $("autofotos-current"),
  count:   $("autofotos-count"),
  bar:     $("autofotos-bar"),
  success: $("autofotos-success"),
  failed:  $("autofotos-failed"),
  skipped: $("autofotos-skipped"),
  closeBtn:$("modal-autofotos-close"),
  startBtn:$("btn-auto-fotos"),
};

let afPolling = null;

function openAutoFotosModal() {
  afEls.desc.textContent = "Consultando o Mercado Livre para cada produto do catálogo...";
  afEls.current.textContent = "Iniciando...";
  afEls.count.textContent = "0 / 0";
  afEls.bar.style.width = "0%";
  afEls.success.textContent = "0";
  afEls.failed.textContent = "0";
  afEls.skipped.textContent = "0";
  afEls.closeBtn.disabled = true;
  afEls.closeBtn.textContent = "Aguarde...";
  afEls.overlay.classList.add("active");
}

function closeAutoFotosModal() {
  afEls.overlay.classList.remove("active");
  if (afPolling) { clearInterval(afPolling); afPolling = null; }
}

function updateAutoFotosUI(st) {
  const total = st.total || 1;
  const pct = Math.round((st.processed / total) * 100);
  afEls.bar.style.width = pct + "%";
  afEls.count.textContent = `${st.processed} / ${st.total}`;
  afEls.current.textContent = st.current || "Processando...";
  afEls.success.textContent = st.success;
  afEls.failed.textContent = st.failed;
  afEls.skipped.textContent = st.skipped;

  if (!st.running && st.processed > 0) {
    // Concluído
    afEls.desc.textContent = "✅ Processo concluído!";
    afEls.current.textContent = "Finalizado";
    afEls.bar.style.width = "100%";
    afEls.closeBtn.disabled = false;
    afEls.closeBtn.textContent = "Fechar e atualizar catálogo";
    if (afPolling) { clearInterval(afPolling); afPolling = null; }
    showToast(`Auto-fotos finalizado: ${st.success} fotos encontradas!`, "success", 5000);
  }
}

async function startAutoFotos() {
  openAutoFotosModal();

  try {
    const res = await fetch(`${API_BASE}/api/catalogo/auto-fotos`, { method: "POST" });
    if (res.status === 409) {
      showToast("O processo já está em execução.", "warning");
      // Poll anyway to show existing progress
    } else if (!res.ok) {
      throw new Error("Erro ao iniciar auto-fotos.");
    }
  } catch (err) {
    afEls.desc.textContent = "❌ " + err.message;
    afEls.closeBtn.disabled = false;
    afEls.closeBtn.textContent = "Fechar";
    return;
  }

  // Polling a cada 2s
  afPolling = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/catalogo/auto-fotos/status`);
      const st = await res.json();
      updateAutoFotosUI(st);
    } catch { /* ignore polling errors */ }
  }, 2000);
}

afEls.startBtn.addEventListener("click", startAutoFotos);
afEls.closeBtn.addEventListener("click", async () => {
  closeAutoFotosModal();
  await loadCatalogo(); // Recarrega catálogo com as novas fotos
});
afEls.overlay.addEventListener("click", (e) => {
  // Só permite fechar clicando fora se não estiver rodando
  if (e.target === afEls.overlay && !afEls.closeBtn.disabled) closeAutoFotosModal();
});

// ── Init ──────────────────────────────────────────────────────────────────────

(async function init() {
  try {
    await fetch(`${API_BASE}/api/health`);
    showToast("Sistema conectado.", "success", 2000);
  } catch {
    showToast("⚠️ Servidor offline. Inicie com: python main.py", "error", 8000);
  }
  
  // Recuperar estado de navegação
  const savedMaster = sessionStorage.getItem('compras_master');
  const savedDir = sessionStorage.getItem('compras_dir');
  if (savedMaster) state.activeMasterCatalog = savedMaster;
  if (savedDir) state.activeDirectory = savedDir;
  
  await loadCatalogo();
})();
