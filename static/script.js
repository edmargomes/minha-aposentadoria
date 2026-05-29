let evolutionChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

async function initApp() {
    await updateDashboard();
    await updateAssetsList();
    await updateContributionsList();
    await initChart();
}

function setupEventListeners() {
    // Asset events
    document.getElementById('btn-add-asset').addEventListener('click', () => openAssetModal());
    document.getElementById('btn-asset-cancel').addEventListener('click', closeAssetModal);
    document.getElementById('btn-asset-delete').addEventListener('click', deleteAsset);
    document.getElementById('asset-form').addEventListener('submit', saveAsset);
    
    document.getElementById('btn-asset-mode-contribution').addEventListener('click', () => setAssetMode('contribution'));
    document.getElementById('btn-asset-mode-balance').addEventListener('click', () => setAssetMode('balance'));

    // Settings events
    document.getElementById('btn-settings').addEventListener('click', openSettingsModal);
    document.getElementById('btn-settings-cancel').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
    
    // Global click outside to close modals
    let lastMouseDownTarget = null;
    window.addEventListener('mousedown', (e) => {
        lastMouseDownTarget = e.target;
    });

    window.onclick = (event) => {
        if (event.target.id.endsWith('-modal') && event.target === lastMouseDownTarget) {
            event.target.classList.add('hidden');
        }
    };
}

// --- DASHBOARD ---

async function updateDashboard() {
    try {
        const response = await fetch('/api/dashboard/metrics');
        const metrics = await response.json();
        
        document.getElementById('metric-monthly-target').innerText = formatCurrency(metrics.monthly_target);
        document.getElementById('metric-invested-month').innerText = formatCurrency(metrics.invested_this_month);
        
        const progressBar = document.getElementById('month-progress-bar');
        const statusMonth = document.getElementById('status-month');
        progressBar.style.width = `${metrics.month_progress}%`;
        
        if (metrics.month_progress >= 100) {
            statusMonth.innerText = 'Meta Atingida';
            statusMonth.className = 'text-xs font-bold px-2 py-1 rounded-full bg-green-100 text-green-700';
            progressBar.className = 'bg-green-600 h-2 rounded-full';
        } else {
            statusMonth.innerText = 'Pendente';
            statusMonth.className = 'text-xs font-bold px-2 py-1 rounded-full bg-yellow-100 text-yellow-700';
            progressBar.className = 'bg-yellow-500 h-2 rounded-full';
        }

        document.getElementById('metric-current-equity').innerText = formatCurrency(metrics.current_equity);
        document.getElementById('metric-profitability').innerText = `${metrics.profitability.toFixed(1)}%`;
        document.getElementById('metric-total-invested').innerText = formatCurrency(metrics.total_invested);
        document.getElementById('metric-remaining-amount').innerText = formatCurrency(metrics.remaining_amount);
        document.getElementById('metric-overall-progress').innerText = `${metrics.overall_progress.toFixed(1)}%`;
        
        const years = (metrics.target_months / 12).toFixed(1).replace('.0', '');
        document.getElementById('label-total-goal').innerText = `Meta Total (${years} anos)`;
        document.getElementById('metric-total-goal').innerText = formatCurrency(metrics.total_goal);
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// --- ASSETS (PATRIMONY) ---

async function updateAssetsList() {
    try {
        const response = await fetch('/api/investments');
        const assets = await response.json();
        const listContainer = document.getElementById('assets-list');
        const emptyState = document.getElementById('assets-empty-state');
        
        const cards = listContainer.querySelectorAll('.asset-card');
        cards.forEach(card => card.remove());
        
        if (assets.length === 0) {
            emptyState.classList.remove('hidden');
        } else {
            emptyState.classList.add('hidden');
            assets.forEach(asset => {
                const card = createAssetCard(asset);
                listContainer.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error updating assets list:', error);
    }
}

function createAssetCard(asset) {
    const div = document.createElement('div');
    div.className = 'asset-card bg-white p-4 rounded-xl shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition duration-200';
    div.onclick = () => openAssetModal(asset.id);
    
    let yieldHtml = '';
    if (asset.total_invested !== null) {
        const yieldAmount = asset.current_value - asset.total_invested;
        const colorClass = yieldAmount > 0 ? 'text-green-600' : (yieldAmount < 0 ? 'text-red-600' : 'hidden');
        const icon = yieldAmount > 0 ? '↑' : '↓';
        if (Math.abs(yieldAmount) > 0.01) {
            yieldHtml = `<span class="${colorClass} text-xs font-bold flex items-center gap-1">${icon} ${formatCurrency(Math.abs(yieldAmount))}</span>`;
        }
    }

    div.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div>
                <h3 class="font-bold text-gray-900 leading-tight">${asset.name}</h3>
                <p class="text-xs text-gray-400">${asset.institution || 'Geral'}</p>
            </div>
            ${yieldHtml}
        </div>
        <p class="text-xl font-black text-gray-800">${formatCurrency(asset.current_value)}</p>
    `;
    return div;
}

async function openAssetModal(assetId = null) {
    const modal = document.getElementById('asset-modal');
    const title = document.getElementById('asset-modal-title');
    const deleteBtn = document.getElementById('btn-asset-delete');
    const actionsDiv = document.getElementById('asset-update-actions');
    const historySection = document.getElementById('asset-history-section');
    const idInput = document.getElementById('asset-id');
    const nameInput = document.getElementById('asset-name');
    const instInput = document.getElementById('asset-institution');
    const valInput = document.getElementById('asset-value');
    
    // Reset
    idInput.value = assetId || '';
    nameInput.value = '';
    instInput.value = '';
    valInput.value = '';
    deleteBtn.classList.add('hidden');
    actionsDiv.classList.add('hidden');
    historySection.classList.add('hidden');
    setAssetMode('balance'); // Default mode

    if (assetId) {
        title.innerText = 'Gerenciar Ativo';
        try {
            const response = await fetch(`/api/investments/${assetId}`);
            const asset = await response.json();
            
            nameInput.value = asset.name;
            instInput.value = asset.institution || '';
            
            // Show update actions for existing assets
            actionsDiv.classList.remove('hidden');
            deleteBtn.classList.remove('hidden');
            
            // Render history
            if (asset.history && asset.history.length > 0) {
                historySection.classList.remove('hidden');
                const list = document.getElementById('asset-history-list');
                list.innerHTML = asset.history.map((h, index) => `
                    <div class="flex justify-between items-center py-2 text-xs border-b border-gray-50 last:border-0 group">
                        <div class="flex flex-col">
                            <span class="text-gray-500">${new Date(h.date + 'T12:00:00').toLocaleDateString('pt-BR')}</span>
                            <span class="font-bold ${h.type === 'contribution' ? 'text-blue-600' : 'text-gray-400'} uppercase text-[9px]">
                                ${h.type === 'contribution' ? 'Valor Aportado' : 'Saldo Total Informado'}
                            </span>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="font-bold text-gray-700">${formatCurrency(h.value)}</span>
                            <button type="button" onclick="deleteHistoryEntry(event, ${h.id}, ${asset.id})" class="text-red-300 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                `).join('');
                
                // Prefill value with calculated current balance
                valInput.value = asset.current_value;
            }
        } catch (error) { console.error(error); }
    } else {
        title.innerText = 'Novo Ativo';
        // For new assets, we just want the initial value (contribution)
        setAssetMode('contribution');
        document.getElementById('label-asset-value').innerText = 'Valor Inicial (R$)';
    }

    modal.classList.remove('hidden');
}

function setAssetMode(mode) {
    const btnCont = document.getElementById('btn-asset-mode-contribution');
    const btnBal = document.getElementById('btn-asset-mode-balance');
    const label = document.getElementById('label-asset-value');
    const help = document.getElementById('help-asset-value');
    const actionInput = document.getElementById('asset-action-type');
    
    if (!actionInput) return; // Guard for script initialization

    actionInput.value = mode;
    
    if (mode === 'contribution') {
        btnCont.classList.add('border-blue-500', 'bg-blue-50');
        btnCont.classList.remove('border-blue-100');
        btnBal.classList.add('border-gray-100');
        btnBal.classList.remove('border-blue-500', 'bg-blue-50');
        
        label.innerText = 'Valor do Aporte (R$)';
        help.innerText = 'Este valor será somado ao custo do ativo e considerado no cálculo de rentabilidade.';
        help.classList.remove('hidden');
    } else {
        btnBal.classList.add('border-blue-500', 'bg-blue-50');
        btnBal.classList.remove('border-gray-100');
        btnCont.classList.add('border-blue-100');
        btnCont.classList.remove('border-blue-500', 'bg-blue-50');
        
        label.innerText = 'Saldo Real Atual (R$)';
        help.innerText = 'Informe o valor total que aparece no seu extrato hoje para calcularmos os ganhos.';
        help.classList.remove('hidden');
    }
}

function closeAssetModal() { document.getElementById('asset-modal').classList.add('hidden'); }

async function saveAsset(e) {
    e.preventDefault();
    const id = document.getElementById('asset-id').value;
    const name = document.getElementById('asset-name').value;
    const institution = document.getElementById('asset-institution').value;
    const value = parseFloat(document.getElementById('asset-value').value);
    const type = document.getElementById('asset-action-type').value;

    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/investments/${id}` : '/api/investments';
    const body = { name, institution, value, type };

    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (response.ok) { closeAssetModal(); initApp(); }
    } catch (error) { console.error(error); }
}

async function deleteAsset() {
    const id = document.getElementById('asset-id').value;
    if (confirm('Deseja excluir este ativo?')) {
        try {
            await fetch(`/api/investments/${id}`, { method: 'DELETE' });
            closeAssetModal(); initApp();
        } catch (error) { console.error(error); }
    }
}

// --- CONTRIBUTIONS (EFFORT) ---

async function updateContributionsList() {
    try {
        const response = await fetch('/api/contributions');
        const contributions = await response.json();
        const listContainer = document.getElementById('contributions-list');
        const emptyState = document.getElementById('contributions-empty-state');

        listContainer.innerHTML = '';
        if (contributions.length === 0) {
            listContainer.appendChild(emptyState);
        } else {
            contributions.forEach(c => {
                const item = document.createElement('div');
                item.className = 'flex justify-between items-center p-3 border-b border-gray-50 last:border-0 hover:bg-gray-50';
                item.innerHTML = `
                    <div>
                        <p class="font-bold text-gray-800 text-sm">${formatCurrency(c.amount)}</p>
                        <p class="text-[10px] text-gray-400 uppercase font-bold">${c.description || 'Aporte Mensal'}</p>
                    </div>
                    <span class="text-[10px] bg-green-50 text-green-600 px-2 py-1 rounded-md font-bold">${new Date(c.date + 'T12:00:00').toLocaleDateString('pt-BR')}</span>
                `;
                listContainer.appendChild(item);
            });
        }
    } catch (error) { console.error(error); }
}

async function deleteHistoryEntry(event, historyId, assetId) {
    event.stopPropagation();
    if (confirm('Deseja excluir este registro do histórico?')) {
        try {
            const response = await fetch(`/api/investments/history/${historyId}`, { method: 'DELETE' });
            if (response.ok) {
                // Refresh modal and dashboard
                openAssetModal(assetId);
                initApp();
            }
        } catch (error) { console.error(error); }
    }
}

// --- SETTINGS ---

async function openSettingsModal() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        document.getElementById('setting-goal').value = settings.target_goal;
        document.getElementById('setting-initial-wealth').value = settings.initial_wealth || 0;
        document.getElementById('setting-rate').value = settings.annual_interest_rate;
        document.getElementById('setting-months').value = settings.target_months;
        document.getElementById('settings-modal').classList.remove('hidden');
    } catch (error) { console.error(error); }
}

function closeSettingsModal() { document.getElementById('settings-modal').classList.add('hidden'); }

async function saveSettings(e) {
    e.preventDefault();
    const target_goal = parseFloat(document.getElementById('setting-goal').value);
    const initial_wealth = parseFloat(document.getElementById('setting-initial-wealth').value);
    const annual_interest_rate = parseFloat(document.getElementById('setting-rate').value);
    const target_months = parseInt(document.getElementById('setting-months').value);
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_goal, initial_wealth, annual_interest_rate, target_months })
        });
        if (response.ok) { closeSettingsModal(); initApp(); }
    } catch (error) { console.error(error); }
}

// --- CHART ---

async function initChart() {
    try {
        const response = await fetch('/api/chart/data');
        const data = await response.json();
        const ctx = document.getElementById('evolutionChart').getContext('2d');
        if (evolutionChart) evolutionChart.destroy();
        
        evolutionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Projeção Ideal (Meta)',
                        data: data.ideal_projection,
                        borderColor: '#378ADD',
                        backgroundColor: 'rgba(55, 138, 221, 0.05)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Expectativa de Saldo',
                        data: data.wealth_projection,
                        borderColor: '#f59e0b', // Amber/Orange
                        borderWidth: 2,
                        borderDash: [5, 5], // Dashed line
                        pointRadius: 0,
                        tension: 0.3,
                        fill: false
                    },
                    {
                        label: 'Patrimônio Real (Atualizado)',
                        data: data.actual_equity,
                        borderColor: '#10b981',
                        backgroundColor: '#10b981',
                        borderWidth: 4,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        spanGaps: true,
                        showLine: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, padding: 20 } },
                    tooltip: { mode: 'index', intersect: false, callbacks: { label: (c) => `${c.dataset.label}: ${formatCurrency(c.parsed.y)}` } }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { callback: (v) => v >= 1000 ? `R$ ${v/1000}k` : `R$ ${v}` } },
                    x: { grid: { display: false } }
                }
            }
        });
    } catch (error) { console.error(error); }
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
}
