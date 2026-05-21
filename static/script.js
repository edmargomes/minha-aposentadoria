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
    
    // Contribution events
    document.getElementById('btn-add-contribution').addEventListener('click', () => openContributionModal());
    document.getElementById('btn-cont-cancel').addEventListener('click', closeContributionModal);
    document.getElementById('contribution-form').addEventListener('submit', saveContribution);

    // Settings events
    document.getElementById('btn-settings').addEventListener('click', openSettingsModal);
    document.getElementById('btn-settings-cancel').addEventListener('click', closeSettingsModal);
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
    
    // Global click outside to close modals
    window.onclick = (event) => {
        if (event.target.id.endsWith('-modal')) {
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
    
    let variationHtml = '';
    if (asset.previous_value !== null) {
        const diff = asset.current_value - asset.previous_value;
        const colorClass = diff >= 0 ? 'text-green-600' : 'text-red-600';
        const icon = diff >= 0 ? '↑' : '↓';
        if (diff !== 0) {
            variationHtml = `<span class="${colorClass} text-xs font-bold flex items-center gap-1">${icon} ${formatCurrency(Math.abs(diff))}</span>`;
        }
    }

    div.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div>
                <h3 class="font-bold text-gray-900 leading-tight">${asset.name}</h3>
                <p class="text-xs text-gray-400">${asset.institution || 'Geral'}</p>
            </div>
            ${variationHtml}
        </div>
        <p class="text-xl font-black text-gray-800">${formatCurrency(asset.current_value)}</p>
    `;
    return div;
}

async function openAssetModal(assetId = null) {
    const modal = document.getElementById('asset-modal');
    const form = document.getElementById('asset-form');
    const title = document.getElementById('asset-modal-title');
    const btnDelete = document.getElementById('btn-asset-delete');
    const historySection = document.getElementById('asset-history-section');
    
    form.reset();
    document.getElementById('asset-id').value = assetId || '';
    
    if (assetId) {
        title.innerText = 'Editar Ativo';
        btnDelete.classList.remove('hidden');
        historySection.classList.remove('hidden');
        try {
            const response = await fetch(`/api/investments/${assetId}`);
            const asset = await response.json();
            document.getElementById('asset-name').value = asset.name;
            document.getElementById('asset-institution').value = asset.institution || '';
            document.getElementById('asset-value').value = asset.history[0].value;
            
            const historyList = document.getElementById('asset-history-list');
            historyList.innerHTML = asset.history.map(h => `
                <div class="flex justify-between py-1 text-xs border-b border-gray-50 last:border-0">
                    <span class="text-gray-400">${new Date(h.date + 'T12:00:00').toLocaleDateString('pt-BR')}</span>
                    <span class="font-medium text-gray-600">${formatCurrency(h.value)}</span>
                </div>
            `).join('');
        } catch (error) { console.error(error); }
    } else {
        title.innerText = 'Novo Ativo';
        btnDelete.classList.add('hidden');
        historySection.classList.add('hidden');
    }
    modal.classList.remove('hidden');
}

function closeAssetModal() { document.getElementById('asset-modal').classList.add('hidden'); }

async function saveAsset(e) {
    e.preventDefault();
    const id = document.getElementById('asset-id').value;
    const name = document.getElementById('asset-name').value;
    const institution = document.getElementById('asset-institution').value;
    const value = parseFloat(document.getElementById('asset-value').value);
    const url = id ? `/api/investments/${id}` : '/api/investments';
    const method = id ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, institution, value })
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

function openContributionModal() { document.getElementById('contribution-modal').classList.remove('hidden'); }
function closeContributionModal() { document.getElementById('contribution-modal').classList.add('hidden'); }

async function saveContribution(e) {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('cont-amount').value);
    const description = document.getElementById('cont-desc').value;
    
    try {
        const response = await fetch('/api/contributions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, description })
        });
        if (response.ok) { closeContributionModal(); initApp(); }
    } catch (error) { console.error(error); }
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
