/* ═══════════════════════════════════════════════════
   BidRoute AI — SPA Main Application
   ═══════════════════════════════════════════════════ */

// ── API Client ──
const api = {
    async get(url) {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
    async post(url, body) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            let detail = `HTTP ${resp.status}`;
            try { const j = await resp.json(); detail = j.detail || detail; } catch {}
            throw new Error(detail);
        }
        return resp.json();
    },
    async put(url, body) {
        const resp = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
    async del(url) {
        const resp = await fetch(url, { method: 'DELETE' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return resp.json();
    },
};

// ── Toast Notifications ──
function showToast(msg, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="material-symbols-outlined">${type === 'error' ? 'error' : type === 'success' ? 'check_circle' : 'info'}</span>${msg}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Helpers ──
function timeAgo(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'только что';
    if (diff < 3600) return `${Math.floor(diff / 60)} мин. назад`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ч. назад`;
    return `${Math.floor(diff / 86400)} дн. назад`;
}

function statusLabel(status) {
    const labels = {
        new: 'Новая', distributing: 'Рассылка', fully_notified: 'Разослано',
        expired: 'Истекла', sent: 'Отправлено', failed: 'Ошибка',
        pending: 'Ожидание', waiting: 'Ожидание ответа', responded: 'Ответили',
        timeout: 'Таймаут', escalated: 'Эскалация',
    };
    return labels[status] || status;
}

function badge(status) {
    return `<span class="badge ${status}">${statusLabel(status)}</span>`;
}

// ── Router ──
const routes = {
    '/': renderDashboard,
    '/bids': renderBids,
    '/suppliers': renderSuppliers,
    '/rules': renderRules,
    '/logs': renderLogs,
    '/smtp': renderSmtp,
    '/campaigns': renderCampaigns,
    '/monitor': renderMonitor,
};

const pageTitles = {
    '/': 'Дашборд',
    '/bids': 'Заявки',
    '/suppliers': 'Поставщики',
    '/rules': 'Правила маршрутизации',
    '/logs': 'Логи рассылки',
    '/smtp': 'SMTP-аккаунты',
    '/campaigns': 'Рассылки',
    '/monitor': 'Мониторинг umit.pro',
};

function navigateTo(path) {
    window.location.hash = path;
}

function getRoute() {
    const hash = window.location.hash.replace('#', '') || '/';
    return hash;
}

async function handleRoute() {
    const route = getRoute();

    // Check for dynamic bid logs route: /bids/123/logs
    const bidLogsMatch = route.match(/^\/bids\/(\d+)\/logs$/);
    if (bidLogsMatch) {
        const bidId = parseInt(bidLogsMatch[1]);
        document.getElementById('page-title').textContent = 'Логи рассылки по заявке';
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === 'bids');
        });
        const content = document.getElementById('content-area');
        content.innerHTML = '<div class="spinner"></div>';
        try {
            await renderBidLogs(content, bidId);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
        }
        return;
    }

    // Check for dynamic bid search results route: /bids/123/search
    const bidSearchMatch = route.match(/^\/bids\/(\d+)\/search$/);
    if (bidSearchMatch) {
        const bidId = parseInt(bidSearchMatch[1]);
        document.getElementById('page-title').textContent = 'Результаты поиска поставщиков';
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === 'bids');
        });
        const content = document.getElementById('content-area');
        content.innerHTML = '<div class="spinner"></div>';
        try {
            await renderBidSearch(content, bidId);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
        }
        return;
    }

    // Check for campaign detail route: /campaigns/123
    const campaignMatch = route.match(/^\/campaigns\/(\d+)$/);
    if (campaignMatch) {
        const campaignId = parseInt(campaignMatch[1]);
        document.getElementById('page-title').textContent = 'Детали кампании';
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === 'campaigns');
        });
        const content = document.getElementById('content-area');
        content.innerHTML = '<div class="spinner"></div>';
        try {
            await renderCampaignDetail(content, campaignId);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
        }
        return;
    }

    const renderFn = routes[route] || renderDashboard;
    const title = pageTitles[route] || 'Дашборд';

    document.getElementById('page-title').textContent = title;

    // Update active nav
    document.querySelectorAll('.nav-item').forEach(item => {
        const page = item.dataset.page;
        const isActive = (route === '/' && page === 'dashboard') ||
            (route === `/${page}`);
        item.classList.toggle('active', isActive);
    });

    const content = document.getElementById('content-area');
    content.innerHTML = '<div class="spinner"></div>';

    try {
        await renderFn(content);
    } catch (e) {
        content.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
    }
}

window.addEventListener('hashchange', handleRoute);

// ── System Status Polling ──
async function updateSystemStatus() {
    try {
        const status = await api.get('/api/system/status');
        const parserEl = document.getElementById('parser-status');
        const smtpEl = document.getElementById('smtp-status');
        const dotEl = document.getElementById('system-dot');

        if (parserEl) {
            parserEl.textContent = status.parser_running ? 'Активен' : 'Остановлен';
            parserEl.className = `status-value ${status.parser_running ? 'online' : 'offline'}`;
        }
        if (smtpEl) {
            smtpEl.textContent = status.smtp_configured ? 'Настроен' : 'Не настроен';
            smtpEl.className = `status-value ${status.smtp_configured ? 'online' : 'offline'}`;
        }
        if (dotEl) {
            dotEl.className = `status-dot ${status.parser_running ? 'online' : ''}`;
        }
    } catch (e) { /* silent */ }
}

// ═══════════════════════════════════════════════════
//  PAGE: Dashboard
// ═══════════════════════════════════════════════════
async function renderDashboard(container) {
    const [stats, recent, analytics] = await Promise.all([
        api.get('/api/dashboard/stats'),
        api.get('/api/dashboard/recent?limit=8'),
        api.get('/api/dashboard/analytics').catch(() => null),
    ]);

    container.innerHTML = `
        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-header">
                    <div class="kpi-icon primary"><span class="material-symbols-outlined">analytics</span></div>
                </div>
                <div class="kpi-label">Всего заявок</div>
                <div class="kpi-value">${stats.total_bids}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <div class="kpi-icon info"><span class="material-symbols-outlined">mail</span></div>
                </div>
                <div class="kpi-label">Активные рассылки</div>
                <div class="kpi-value">${stats.active_mailings}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <div class="kpi-icon success"><span class="material-symbols-outlined">how_to_reg</span></div>
                </div>
                <div class="kpi-label">Поставщиков оповещено</div>
                <div class="kpi-value">${stats.suppliers_notified}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <div class="kpi-icon warning"><span class="material-symbols-outlined">percent</span></div>
                </div>
                <div class="kpi-label">Отклик</div>
                <div class="kpi-value">${stats.response_rate}%</div>
            </div>
        </div>

        ${analytics && analytics.spam_alert ? `
        <div class="card mb-24" style="padding:16px;background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;border-radius:12px;display:flex;align-items:center;gap:12px">
            <span class="material-symbols-outlined" style="font-size:28px">warning</span>
            <div>
                <strong>⚠️ Внимание: процент переходов упал!</strong><br>
                <span style="font-size:13px;opacity:0.9">На этой неделе ${analytics.rate_this_week}% (пред. ${analytics.rate_prev_week}%). Возможно, адрес попал в спам.</span>
            </div>
        </div>` : ''}

        ${analytics ? `
        <!-- Analytics Section -->
        <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:24px">
            <div class="kpi-card">
                <div class="kpi-label">Заявок за неделю</div>
                <div class="kpi-value">${analytics.bids_week}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Заявок за месяц</div>
                <div class="kpi-value">${analytics.bids_month}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">% переходов (общий)</div>
                <div class="kpi-value" style="color:${analytics.click_rate > 5 ? 'var(--success)' : analytics.click_rate > 0 ? 'var(--warning)' : 'var(--text-muted)'}">${analytics.click_rate}%</div>
            </div>
        </div>

        <div class="grid-1-2 mb-24">
            <div class="card" style="padding:20px">
                <h3 style="margin:0 0 12px;font-size:15px">📊 Отправки за 14 дней</h3>
                <div style="display:flex;align-items:flex-end;gap:3px;height:80px">
                    ${analytics.daily_chart.map(d => {
        const maxVal = Math.max(...analytics.daily_chart.map(x => x.sent), 1);
        const h = Math.max(4, (d.sent / maxVal) * 70);
        const day = d.date.slice(8);
        return `<div style="flex:1;display:flex;flex-direction:column;align-items:center">
                            <div style="width:100%;height:${h}px;background:${d.sent > 0 ? 'var(--primary)' : '#e2e8f0'};border-radius:3px 3px 0 0;opacity:0.8" title="${d.date}: ${d.sent} отпр."></div>
                            <span style="font-size:9px;color:var(--text-muted);margin-top:4px">${day}</span>
                        </div>`;
    }).join('')}
                </div>
            </div>

            <div class="card" style="padding:20px">
                <h3 style="margin:0 0 12px;font-size:15px">📈 Статистика по всем письмам</h3>
                <div style="display:flex;gap:16px">
                    <div style="flex:1;text-align:center;padding:12px;background:var(--bg);border-radius:8px">
                        <div style="font-size:24px;font-weight:700;color:var(--primary)">${analytics.sent_total}</div>
                        <div style="font-size:12px;color:var(--text-muted)">Отправлено</div>
                    </div>
                    <div style="flex:1;text-align:center;padding:12px;background:var(--bg);border-radius:8px">
                        <div style="font-size:24px;font-weight:700;color:var(--success)">${analytics.clicked_total}</div>
                        <div style="font-size:12px;color:var(--text-muted)">Кликов</div>
                    </div>
                    <div style="flex:1;text-align:center;padding:12px;background:var(--bg);border-radius:8px">
                        <div style="font-size:24px;font-weight:700;color:${analytics.failed_total > 0 ? 'var(--danger)' : 'var(--text-muted)'}">${analytics.failed_total}</div>
                        <div style="font-size:12px;color:var(--text-muted)">Ошибок</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid-1-2 mb-24">
            <div class="card" style="padding:20px">
                <h3 style="margin:0 0 12px;font-size:15px">🏷️ Топ-5 категорий</h3>
                ${analytics.top_categories.length === 0 ? '<p style="color:var(--text-muted)">Нет данных</p>' :
                analytics.top_categories.map((c, i) => `
                    <div style="display:flex;justify-content:space-between;padding:6px 0;${i < analytics.top_categories.length - 1 ? 'border-bottom:1px solid var(--border)' : ''}">
                        <span>${c.name}</span>
                        <span style="font-weight:600">${c.count}</span>
                    </div>
                `).join('')}
            </div>
            <div class="card" style="padding:20px">
                <h3 style="margin:0 0 12px;font-size:15px">⭐ Топ-5 поставщиков (по кликам)</h3>
                ${analytics.top_suppliers.length === 0 ? '<p style="color:var(--text-muted)">Нет кликов</p>' :
                analytics.top_suppliers.map((s, i) => `
                    <div style="display:flex;justify-content:space-between;padding:6px 0;${i < analytics.top_suppliers.length - 1 ? 'border-bottom:1px solid var(--border)' : ''}">
                        <span>${s.name}</span>
                        <span style="font-weight:600;color:var(--success)">${s.clicks} ✓</span>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}
        <!-- Recent Activity Table -->
        <div class="card mb-24">
            <div class="card-header">
                <div>
                    <h3>Последние заявки</h3>
                    <p>Свежие заявки с umit.pro</p>
                </div>
                <a href="#/bids" class="btn btn-sm btn-secondary">Все заявки <span class="material-symbols-outlined">arrow_forward</span></a>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID источника</th>
                        <th>Название</th>
                        <th>Категория</th>
                        <th>Время</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                    ${recent.length === 0 ? '<tr><td colspan="5" style="text-align:center;padding:32px;color:var(--text-muted)">Пока нет заявок. Нажмите «Запустить парсинг» ниже.</td></tr>' : ''}
                    ${recent.map(b => `
                        <tr>
                            <td class="source-id" onclick="navigateTo('/bids')">UM-${b.source_id}</td>
                            <td style="font-weight:500">${b.name}</td>
                            <td>${b.spare_part_type ? `<span class="badge pending">${b.spare_part_type}</span>` : '—'}</td>
                            <td style="color:var(--text-muted)">${timeAgo(b.parsed_at)}</td>
                            <td>${badge(b.status)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <!-- Bottom Grid -->
        <div class="grid-1-2">
            <!-- Quick Controls -->
            <div class="card">
                <div class="card-header"><h3>Быстрые действия</h3></div>
                <div class="card-body" style="display:flex;flex-direction:column;gap:10px">
                    <div class="quick-control" id="btn-trigger-parse">
                        <div class="qc-left">
                            <span class="material-symbols-outlined">refresh</span>
                            <span class="qc-label">Запустить парсинг</span>
                        </div>
                        <span class="material-symbols-outlined" style="font-size:16px;color:var(--text-muted)">chevron_right</span>
                    </div>
                    <div class="quick-control" onclick="navigateTo('/suppliers')">
                        <div class="qc-left">
                            <span class="material-symbols-outlined">person_add</span>
                            <span class="qc-label">Добавить поставщика</span>
                        </div>
                        <span class="material-symbols-outlined" style="font-size:16px;color:var(--text-muted)">chevron_right</span>
                    </div>
                    <div class="quick-control" onclick="navigateTo('/rules')">
                        <div class="qc-left">
                            <span class="material-symbols-outlined">settings</span>
                            <span class="qc-label">Настроить правила</span>
                        </div>
                        <span class="material-symbols-outlined" style="font-size:16px;color:var(--text-muted)">chevron_right</span>
                    </div>
                </div>
            </div>

            <!-- Stats Summary -->
            <div class="card">
                <div class="card-header"><h3>Сводка по системе</h3></div>
                <div class="card-body">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                        <div style="padding:16px;background:var(--bg-input);border-radius:var(--radius)">
                            <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;font-weight:600">Поставщиков в базе</div>
                            <div style="font-size:24px;font-weight:800;margin-top:4px">${stats.total_suppliers}</div>
                        </div>
                        <div style="padding:16px;background:var(--bg-input);border-radius:var(--radius)">
                            <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;font-weight:600">Активных рассылок</div>
                            <div style="font-size:24px;font-weight:800;margin-top:4px">${stats.active_mailings}</div>
                        </div>
                        <div style="padding:16px;background:var(--bg-input);border-radius:var(--radius)">
                            <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;font-weight:600">Всего заявок</div>
                            <div style="font-size:24px;font-weight:800;margin-top:4px">${stats.total_bids}</div>
                        </div>
                        <div style="padding:16px;background:var(--bg-input);border-radius:var(--radius)">
                            <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;font-weight:600">Процент отклика</div>
                            <div style="font-size:24px;font-weight:800;margin-top:4px">${stats.response_rate}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Bind parse trigger
    document.getElementById('btn-trigger-parse')?.addEventListener('click', async () => {
        showToast('Запуск парсинга...', 'info');
        try {
            const result = await api.post('/api/bids/parse', {});
            showToast(result.message, 'success');
            setTimeout(() => handleRoute(), 1500);
        } catch (e) {
            showToast('Ошибка парсинга: ' + e.message, 'error');
        }
    });
}

// ═══════════════════════════════════════════════════
//  PAGE: Bids
// ═══════════════════════════════════════════════════
let bidsPage = 1;
let bidsStatus = '';

async function renderBids(container) {
    const params = new URLSearchParams({ page: bidsPage, page_size: 15 });
    if (bidsStatus) params.set('status', bidsStatus);

    const data = await api.get(`/api/bids?${params}`);

    container.innerHTML = `
        <div class="action-bar">
            <div class="filter-group">
                <select class="filter-select" id="bid-status-filter">
                    <option value="">Все статусы</option>
                    <option value="new" ${bidsStatus === 'new' ? 'selected' : ''}>Новые</option>
                    <option value="distributing" ${bidsStatus === 'distributing' ? 'selected' : ''}>Рассылка</option>
                    <option value="fully_notified" ${bidsStatus === 'fully_notified' ? 'selected' : ''}>Разослано</option>
                </select>
            </div>
            <button class="btn btn-primary" id="btn-parse-bids">
                <span class="material-symbols-outlined">refresh</span> Запустить парсинг
            </button>
        </div>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Название</th>
                        <th>Бренд / Модель</th>
                        <th>Категория</th>
                        <th>Место доставки</th>
                        <th>Статус</th>
                        <th>Батчей</th>
                        <th>Поиск</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.items.length === 0 ? '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted)">Нет заявок</td></tr>' : ''}
                    ${data.items.map(b => `
                        <tr>
                            <td class="source-id"><a href="#/bids/${b.id}/logs" style="color:var(--primary);text-decoration:none;font-weight:600;cursor:pointer" title="Открыть логи рассылки">UM-${b.source_id}</a></td>
                            <td style="font-weight:500;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${b.name}"><a href="${b.source_url || 'https://umit.pro/public-bids/' + b.source_id}" target="_blank" style="color:inherit;text-decoration:none" onmouseover="this.style.color='var(--primary)'" onmouseout="this.style.color='inherit'">${b.name}</a></td>
                            <td style="color:var(--text-secondary)">${b.brand ? b.brand + ' ' + b.model : '—'}</td>
                            <td>${b.spare_part_type || '—'}</td>
                            <td style="color:var(--text-secondary)">${b.delivery_place || '—'}</td>
                            <td>${badge(b.status)}</td>
                            <td style="text-align:center">${b.batch_count}</td>
                            <td style="text-align:center"><a href="#/bids/${b.id}/search" style="color:var(--primary);text-decoration:none" title="Результаты поиска поставщиков"><span class="material-symbols-outlined" style="font-size:18px">search</span></a></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <div class="pagination" id="bids-pagination"></div>
    `;

    // Pagination
    const totalPages = Math.ceil(data.total / 15);
    renderPagination('bids-pagination', bidsPage, totalPages, (p) => { bidsPage = p; renderBids(container); });

    // Filter
    document.getElementById('bid-status-filter').addEventListener('change', (e) => {
        bidsStatus = e.target.value;
        bidsPage = 1;
        renderBids(container);
    });

    // Parse button
    document.getElementById('btn-parse-bids').addEventListener('click', async () => {
        showToast('Запуск парсинга...', 'info');
        try {
            const result = await api.post('/api/bids/parse', {});
            showToast(result.message, 'success');
            setTimeout(() => renderBids(container), 1500);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });
}

// ═══════════════════════════════════════════════════
//  PAGE: Suppliers
// ═══════════════════════════════════════════════════
let suppliersPage = 1;

async function renderSuppliers(container) {
    const data = await api.get(`/api/suppliers?page=${suppliersPage}&page_size=15&active_only=false`);

    container.innerHTML = `
        <div class="action-bar">
            <div style="font-size:13px;color:var(--text-secondary)">Всего: <strong>${data.total}</strong></div>
            <div style="display:flex;gap:8px">
                <button class="btn btn-secondary" id="btn-ai-search">
                    <span class="material-symbols-outlined">psychology</span> AI Поиск
                </button>
                <button class="btn btn-primary" id="btn-add-supplier">
                    <span class="material-symbols-outlined">person_add</span> Добавить
                </button>
            </div>
        </div>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Компания</th>
                        <th>Email</th>
                        <th>Телефон</th>
                        <th>Категории</th>
                        <th>Регионы</th>
                        <th>Источник</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody id="suppliers-tbody">
                    ${data.items.length === 0 ? '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">Нет поставщиков. Добавьте вручную или используйте AI Поиск.</td></tr>' : ''}
                    ${data.items.map(s => `
                        <tr>
                            <td style="font-weight:600">${s.website ? `<a href="${s.website.startsWith('http') ? s.website : 'https://' + s.website}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none" title="${s.website}">${s.company_name} <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;opacity:0.5">open_in_new</span></a>` : s.company_name}</td>
                            <td style="color:var(--primary)">${s.email}</td>
                            <td style="color:var(--text-secondary)">${s.phone || '—'}</td>
                            <td>${(s.categories || []).map(c => `<span class="badge pending">${c}</span>`).join(' ') || '—'}</td>
                            <td style="color:var(--text-secondary);font-size:12px">${(s.regions || []).join(', ') || '—'}</td>
                            <td><span class="badge ${s.source === 'ai' ? 'distributing' : 'new'}">${s.source === 'ai' ? 'AI' : 'Ручной'}</span></td>
                            <td>
                                <button class="btn btn-sm btn-danger" onclick="deleteSupplier(${s.id})">
                                    <span class="material-symbols-outlined">delete</span>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <div class="pagination" id="suppliers-pagination"></div>
    `;

    const totalPages = Math.ceil(data.total / 15);
    renderPagination('suppliers-pagination', suppliersPage, totalPages, (p) => { suppliersPage = p; renderSuppliers(container); });

    // Add supplier button
    document.getElementById('btn-add-supplier').addEventListener('click', () => showAddSupplierModal(container));

    // AI Search button
    document.getElementById('btn-ai-search').addEventListener('click', () => showAISearchModal(container));
}

window.deleteSupplier = async function (id) {
    if (!confirm('Удалить поставщика?')) return;
    try {
        await api.del(`/api/suppliers/${id}`);
        showToast('Поставщик удалён', 'success');
        handleRoute();
    } catch (e) {
        showToast('Ошибка: ' + e.message, 'error');
    }
};

function showAddSupplierModal(container) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>Добавить поставщика</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Название компании *</label>
                    <input class="form-input" id="s-company" placeholder="ООО «Поставщик»">
                </div>
                <div class="form-group">
                    <label class="form-label">Email *</label>
                    <input class="form-input" id="s-email" type="email" placeholder="info@supplier.ru">
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label class="form-label">Телефон</label>
                        <input class="form-input" id="s-phone" placeholder="+7 (999) 123-45-67">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Контактное лицо</label>
                        <input class="form-input" id="s-contact" placeholder="Иван Иванов">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Категории (через запятую)</label>
                    <input class="form-input" id="s-categories" placeholder="Запчасти, Фильтры, Двигатели">
                </div>
                <div class="form-group">
                    <label class="form-label">Регионы (через запятую)</label>
                    <input class="form-input" id="s-regions" placeholder="Москва, Санкт-Петербург">
                </div>
                <div class="form-group">
                    <label class="form-label">Сайт</label>
                    <input class="form-input" id="s-website" placeholder="https://supplier.ru">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Отмена</button>
                <button class="btn btn-primary" id="btn-save-supplier">Сохранить</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('btn-save-supplier').addEventListener('click', async () => {
        const company = document.getElementById('s-company').value.trim();
        const email = document.getElementById('s-email').value.trim();
        if (!company || !email) return showToast('Заполните обязательные поля', 'error');

        try {
            await api.post('/api/suppliers', {
                company_name: company,
                email: email,
                phone: document.getElementById('s-phone').value.trim(),
                contact_person: document.getElementById('s-contact').value.trim(),
                categories: document.getElementById('s-categories').value.split(',').map(s => s.trim()).filter(Boolean),
                regions: document.getElementById('s-regions').value.split(',').map(s => s.trim()).filter(Boolean),
                website: document.getElementById('s-website').value.trim(),
            });
            overlay.remove();
            showToast('Поставщик добавлен', 'success');
            renderSuppliers(container);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });
}

function showAISearchModal(container) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>AI Поиск поставщиков</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Поисковый запрос</label>
                    <p class="form-hint">Опишите какие поставщики вам нужны. AI найдёт релевантных и добавит в базу.</p>
                    <textarea class="form-input" id="ai-query" rows="3" placeholder="Например: Поставщики запчастей для дробилок Sandvik в Москве"></textarea>
                </div>
                <div id="ai-results" style="display:none">
                    <div style="padding:16px;background:var(--success-bg);border-radius:var(--radius);margin-top:12px">
                        <span id="ai-results-text" style="font-size:13px;color:#047857;font-weight:500"></span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Закрыть</button>
                <button class="btn btn-primary" id="btn-run-ai-search">
                    <span class="material-symbols-outlined">psychology</span> Найти
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('btn-run-ai-search').addEventListener('click', async () => {
        const query = document.getElementById('ai-query').value.trim();
        if (!query) return showToast('Введите запрос', 'error');

        const btn = document.getElementById('btn-run-ai-search');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;margin:0;border-width:2px"></div> Поиск...';

        try {
            const result = await api.post('/api/suppliers/ai-search', { query });
            document.getElementById('ai-results').style.display = 'block';
            document.getElementById('ai-results-text').textContent =
                `Найдено поставщиков: ${result.suppliers_found}. Добавлены в базу.`;
            showToast(`Найдено ${result.suppliers_found} поставщиков`, 'success');
            btn.innerHTML = '<span class="material-symbols-outlined">check</span> Готово';
            setTimeout(() => {
                overlay.remove();
                renderSuppliers(container);
            }, 1500);
        } catch (e) {
            showToast('Ошибка AI поиска: ' + e.message, 'error');
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined">psychology</span> Найти';
        }
    });
}

// ═══════════════════════════════════════════════════
//  PAGE: Rules
// ═══════════════════════════════════════════════════
async function renderRules(container) {
    const rules = await api.get('/api/rules');

    container.innerHTML = `
        <div style="max-width:700px">
            <!-- Schedule -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">schedule</span>
                    <h3>Расписание</h3>
                </div>
                <div class="card-body">
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">Интервал парсинга</label>
                            <p class="form-hint">Как часто проверять новые заявки на umit.pro.</p>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-parse-interval" value="${rules.parse_interval_minutes || 5}" min="1" max="1440">
                                <span class="suffix">минут</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Задержка между письмами</label>
                            <p class="form-hint">Антиспам-пауза между отправкой писем внутри одного батча.</p>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-email-delay" value="${rules.email_delay_seconds || 30}" min="5" max="300">
                                <span class="suffix">секунд</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Batching Logic -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">reorder</span>
                    <h3>Логика пакетирования</h3>
                </div>
                <div class="card-body">
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">Размер пакета</label>
                            <p class="form-hint">Максимальное число поставщиков в одном батче.</p>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch-size" value="${rules.batch_size}" min="1" max="50">
                                <span class="suffix">поставщиков</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Таймаут ожидания</label>
                            <p class="form-hint">Время ожидания перед эскалацией.</p>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch-timeout" value="${rules.batch_timeout_minutes}" min="1" max="1440">
                                <span class="suffix">минут</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Intelligent Matching -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">psychology</span>
                    <h3>Умный подбор</h3>
                </div>
                <div class="card-body">
                    <div class="form-group">
                        <label class="form-label">Чувствительность подбора</label>
                        <p class="form-hint">Строгость совпадения при подборе поставщиков.</p>
                        <input type="range" class="range-slider" id="r-sensitivity" min="0" max="100" value="${Math.round(rules.matching_sensitivity * 100)}">
                        <div class="range-labels">
                            <span style="color:var(--text-muted);font-weight:600">Широкий<br><span style="font-weight:400;font-size:10px">Больше объём</span></span>
                            <span class="center">Баланс (<span id="r-sens-value">${Math.round(rules.matching_sensitivity * 100)}</span>%)</span>
                            <span style="color:var(--text-muted);font-weight:600;text-align:right">Точный<br><span style="font-weight:400;font-size:10px">Выше точность</span></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Keywords -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">filter_alt</span>
                    <h3>Ключевые слова фильтрации</h3>
                </div>
                <div class="card-body">
                    <p class="form-hint" style="margin-bottom:12px">Система будет обрабатывать только заявки, содержащие эти ключевые слова.</p>
                    <div class="tags-container" id="tags-container">
                        ${(rules.filter_keywords || []).map(kw => `
                            <span class="tag">${kw}<button class="tag-remove material-symbols-outlined" data-keyword="${kw}">close</button></span>
                        `).join('')}
                    </div>
                    <div style="display:flex;gap:8px;margin-top:12px">
                        <input class="form-input" id="r-new-keyword" placeholder="Добавить ключевое слово..." style="flex:1">
                        <button class="btn btn-primary" id="btn-add-keyword">Добавить</button>
                    </div>
                </div>
            </div>

            <!-- Auto toggles -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">toggle_on</span>
                    <h3>Автоматизация</h3>
                </div>
                <div class="card-body" style="display:flex;flex-direction:column;gap:16px">
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="r-auto-parse" ${rules.auto_parse ? 'checked' : ''} style="width:18px;height:18px;accent-color:var(--primary)">
                        <div>
                            <span style="font-size:14px;font-weight:600">Автоматический парсинг</span>
                            <p style="font-size:12px;color:var(--text-muted)">Парсер автоматически проверяет новые заявки</p>
                        </div>
                    </label>
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="r-auto-distribute" ${rules.auto_distribute ? 'checked' : ''} style="width:18px;height:18px;accent-color:var(--primary)">
                        <div>
                            <span style="font-size:14px;font-weight:600">Автоматическая рассылка</span>
                            <p style="font-size:12px;color:var(--text-muted)">Автоматически рассылать заявки подходящим поставщикам</p>
                        </div>
                    </label>
                </div>
            </div>

            <!-- Actions Footer -->
            <div style="display:flex;align-items:center;justify-content:space-between;padding-top:16px;border-top:1px solid var(--border)">
                <div class="config-note">
                    <span class="material-symbols-outlined">info</span>
                    <span>Изменения вступят в силу в следующем цикле автоматизации.</span>
                </div>
                <button class="btn btn-primary" id="btn-save-rules" style="flex-shrink:0">
                    <span class="material-symbols-outlined">save</span> Сохранить
                </button>
            </div>
        </div>
    `;

    // Sensitivity slider live update
    document.getElementById('r-sensitivity').addEventListener('input', (e) => {
        document.getElementById('r-sens-value').textContent = e.target.value;
    });

    // Add keyword
    const addKeyword = () => {
        const input = document.getElementById('r-new-keyword');
        const kw = input.value.trim();
        if (!kw) return;
        const container = document.getElementById('tags-container');
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = `${kw}<button class="tag-remove material-symbols-outlined" data-keyword="${kw}">close</button>`;
        container.appendChild(tag);
        input.value = '';
        tag.querySelector('.tag-remove').addEventListener('click', () => tag.remove());
    };

    document.getElementById('btn-add-keyword').addEventListener('click', addKeyword);
    document.getElementById('r-new-keyword').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') addKeyword();
    });

    // Remove keywords
    document.querySelectorAll('.tag-remove').forEach(btn => {
        btn.addEventListener('click', () => btn.closest('.tag').remove());
    });

    // Save rules
    document.getElementById('btn-save-rules').addEventListener('click', async () => {
        const keywords = Array.from(document.querySelectorAll('#tags-container .tag'))
            .map(t => t.textContent.replace('close', '').trim());

        try {
            await api.put('/api/rules', {
                batch_size: parseInt(document.getElementById('r-batch-size').value),
                batch_timeout_minutes: parseInt(document.getElementById('r-batch-timeout').value),
                matching_sensitivity: parseInt(document.getElementById('r-sensitivity').value) / 100,
                filter_keywords: keywords,
                auto_parse: document.getElementById('r-auto-parse').checked,
                auto_distribute: document.getElementById('r-auto-distribute').checked,
                parse_interval_minutes: parseInt(document.getElementById('r-parse-interval').value),
                email_delay_seconds: parseInt(document.getElementById('r-email-delay').value),
            });
            showToast('Настройки сохранены', 'success');
        } catch (e) {
            showToast('Ошибка сохранения: ' + e.message, 'error');
        }
    });
}

// ═══════════════════════════════════════════════════
//  PAGE: Logs
// ═══════════════════════════════════════════════════
let logsPage = 1;
let logsStatus = '';

async function renderLogs(container) {
    const data = await api.get(`/api/logs?page=1&page_size=500`);
    const allLogs = data.items;

    let sortColumn = 'sent_at';
    let sortDir = 'desc';
    let filterStatus = '';
    let filterBatch = '';
    let filterText = '';

    function formatDate(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function getFiltered() {
        let result = [...allLogs];
        if (filterStatus) result = result.filter(l => l.email_status === filterStatus);
        if (filterBatch) result = result.filter(l => String(l.batch_number) === filterBatch);
        if (filterText) {
            const q = filterText.toLowerCase();
            result = result.filter(l =>
                l.bid_name.toLowerCase().includes(q) ||
                l.supplier_name.toLowerCase().includes(q) ||
                l.supplier_email.toLowerCase().includes(q) ||
                String(l.bid_source_id).includes(q) ||
                (l.error_message || '').toLowerCase().includes(q)
            );
        }
        result.sort((a, b) => {
            let va = a[sortColumn], vb = b[sortColumn];
            if (va === null || va === undefined) va = '';
            if (vb === null || vb === undefined) vb = '';
            if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
            return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        });
        return result;
    }

    function sortIcon(col) {
        if (sortColumn !== col) return '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;opacity:0.3">unfold_more</span>';
        return sortDir === 'asc'
            ? '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;color:var(--primary)">arrow_upward</span>'
            : '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;color:var(--primary)">arrow_downward</span>';
    }

    const batches = [...new Set(allLogs.map(l => l.batch_number))].sort((a, b) => a - b);

    function render() {
        const filtered = getFiltered();

        container.innerHTML = `
            <div class="action-bar" style="flex-wrap:wrap">
                <div class="filter-group" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
                    <input class="form-input" type="text" id="gl-search" placeholder="Поиск по заявке, поставщику, email..." value="${filterText}" style="width:260px;height:36px;font-size:13px">
                    <select class="filter-select" id="gl-status-filter" style="height:36px">
                        <option value="">Все статусы</option>
                        <option value="sent" ${filterStatus === 'sent' ? 'selected' : ''}>Отправлено</option>
                        <option value="failed" ${filterStatus === 'failed' ? 'selected' : ''}>Ошибка</option>
                        <option value="opened" ${filterStatus === 'opened' ? 'selected' : ''}>Открыто</option>
                        <option value="responded" ${filterStatus === 'responded' ? 'selected' : ''}>Ответили</option>
                    </select>
                    <select class="filter-select" id="gl-batch-filter" style="height:36px">
                        <option value="">Все батчи</option>
                        ${batches.map(b => `<option value="${b}" ${filterBatch === String(b) ? 'selected' : ''}>#${b}</option>`).join('')}
                    </select>
                </div>
                <div style="font-size:13px;color:var(--text-secondary)">Записей: <strong>${filtered.length}</strong> / ${allLogs.length}</div>
            </div>

            <div class="card">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="gl-sort" data-col="bid_source_id" style="cursor:pointer">Заявка ${sortIcon('bid_source_id')}</th>
                            <th class="gl-sort" data-col="supplier_name" style="cursor:pointer">Поставщик ${sortIcon('supplier_name')}</th>
                            <th class="gl-sort" data-col="supplier_email" style="cursor:pointer">Email ${sortIcon('supplier_email')}</th>
                            <th class="gl-sort" data-col="batch_number" style="cursor:pointer">Батч ${sortIcon('batch_number')}</th>
                            <th class="gl-sort" data-col="email_status" style="cursor:pointer">Статус ${sortIcon('email_status')}</th>
                            <th class="gl-sort" data-col="sent_at" style="cursor:pointer">Отправлено ${sortIcon('sent_at')}</th>
                            <th class="gl-sort" data-col="clicked_at" style="cursor:pointer">Клик ${sortIcon('clicked_at')}</th>
                            <th class="gl-sort" data-col="error_message" style="cursor:pointer">Ошибка ${sortIcon('error_message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtered.length === 0 ? '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted)">Нет записей в логе</td></tr>' : ''}
                        ${filtered.map(log => `
                            <tr>
                                <td style="font-weight:500">
                                    <a href="#/bids/${log.bid_id}/logs" style="color:var(--primary);text-decoration:none;font-weight:600" title="Открыть логи заявки">UM-${log.bid_source_id}</a>
                                    <br><span style="font-size:11px;color:var(--text-muted);max-width:150px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${log.bid_name}</span>
                                </td>
                                <td style="font-weight:500">${log.supplier_name}</td>
                                <td style="color:var(--primary);font-size:12px">${log.supplier_email}</td>
                                <td style="text-align:center;font-weight:600">#${log.batch_number}</td>
                                <td>${badge(log.email_status)}</td>
                                <td style="color:var(--text-muted);font-size:12px;white-space:nowrap">${formatDate(log.sent_at)}</td>
                                <td style="font-size:12px;white-space:nowrap">${log.clicked_at ? '<span style="color:var(--success)">✓ ' + formatDate(log.clicked_at) + '</span>' : '<span style="color:var(--text-muted)">—</span>'}</td>
                                <td style="color:var(--danger);font-size:12px;max-width:150px;overflow:hidden;text-overflow:ellipsis" title="${log.error_message}">${log.error_message || '—'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // Sort handlers
        document.querySelectorAll('.gl-sort').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.col;
                if (sortColumn === col) {
                    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    sortColumn = col;
                    sortDir = 'asc';
                }
                render();
            });
        });

        // Filter handlers
        document.getElementById('gl-status-filter').addEventListener('change', (e) => {
            filterStatus = e.target.value;
            render();
        });
        document.getElementById('gl-batch-filter').addEventListener('change', (e) => {
            filterBatch = e.target.value;
            render();
        });
        document.getElementById('gl-search').addEventListener('input', (e) => {
            filterText = e.target.value;
            render();
        });
    }

    render();
}


// ═══════════════════════════════════════════════════
//  PAGE: Bid Distribution Logs (per bid)
// ═══════════════════════════════════════════════════
async function renderBidLogs(container, bidId) {
    let data;
    try {
        data = await api.get(`/api/bids/${bidId}/logs`);
    } catch (e) {
        container.innerHTML = `<div class="card" style="padding:40px;text-align:center"><p style="color:var(--danger)">Ошибка загрузки: ${e.message}</p><button class="btn btn-primary" onclick="navigateTo('/bids')">← К заявкам</button></div>`;
        return;
    }

    const bid = data.bid;
    let logs = data.logs;
    let sortColumn = 'sent_at';
    let sortDir = 'desc';
    let filterStatus = '';
    let filterBatch = '';
    let filterText = '';

    function formatDate(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }

    function getFiltered() {
        let result = [...logs];
        if (filterStatus) result = result.filter(l => l.email_status === filterStatus);
        if (filterBatch) result = result.filter(l => String(l.batch_number) === filterBatch);
        if (filterText) {
            const q = filterText.toLowerCase();
            result = result.filter(l =>
                l.supplier_name.toLowerCase().includes(q) ||
                l.supplier_email.toLowerCase().includes(q) ||
                (l.error_message || '').toLowerCase().includes(q)
            );
        }
        result.sort((a, b) => {
            let va = a[sortColumn], vb = b[sortColumn];
            if (va === null || va === undefined) va = '';
            if (vb === null || vb === undefined) vb = '';
            if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
            return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        });
        return result;
    }

    function sortIcon(col) {
        if (sortColumn !== col) return '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;opacity:0.3">unfold_more</span>';
        return sortDir === 'asc'
            ? '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;color:var(--primary)">arrow_upward</span>'
            : '<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;color:var(--primary)">arrow_downward</span>';
    }

    // Unique batches for filter
    const batches = [...new Set(logs.map(l => l.batch_number))].sort((a, b) => a - b);

    function render() {
        const filtered = getFiltered();

        container.innerHTML = `
            <div style="margin-bottom:20px">
                <button class="btn" onclick="navigateTo('/bids')" style="gap:4px">
                    <span class="material-symbols-outlined">arrow_back</span> К заявкам
                </button>
            </div>

            <div class="card mb-24" style="padding:20px">
                <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
                    <div>
                        <h3 style="margin:0;font-size:18px">Заявка UM-${bid.source_id}: ${bid.name}</h3>
                        <p style="margin:4px 0 0;color:var(--text-muted);font-size:13px">
                            Статус: ${badge(bid.status)} &nbsp;|&nbsp; Всего отправок: <strong>${logs.length}</strong> &nbsp;|&nbsp; Показано: <strong>${filtered.length}</strong>
                        </p>
                    </div>
                    <a href="${bid.source_url || 'https://umit.pro/public-bids/' + bid.source_id}" target="_blank" class="btn btn-primary" style="gap:4px">
                        <span class="material-symbols-outlined">open_in_new</span> Открыть на Umit
                    </a>
                </div>
            </div>

            <div class="action-bar" style="flex-wrap:wrap">
                <div class="filter-group" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
                    <input class="form-input" type="text" id="bl-search" placeholder="Поиск по имени, email..." value="${filterText}" style="width:220px;height:36px;font-size:13px">
                    <select class="filter-select" id="bl-status-filter" style="height:36px">
                        <option value="">Все статусы</option>
                        <option value="sent" ${filterStatus === 'sent' ? 'selected' : ''}>Отправлено</option>
                        <option value="failed" ${filterStatus === 'failed' ? 'selected' : ''}>Ошибка</option>
                        <option value="opened" ${filterStatus === 'opened' ? 'selected' : ''}>Открыто</option>
                        <option value="responded" ${filterStatus === 'responded' ? 'selected' : ''}>Ответили</option>
                    </select>
                    <select class="filter-select" id="bl-batch-filter" style="height:36px">
                        <option value="">Все батчи</option>
                        ${batches.map(b => `<option value="${b}" ${filterBatch === String(b) ? 'selected' : ''}>#${b}</option>`).join('')}
                    </select>
                </div>
                <div style="font-size:13px;color:var(--text-secondary)">Записей: <strong>${filtered.length}</strong> / ${logs.length}</div>
            </div>

            <div class="card">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-col="batch_number" style="cursor:pointer">Батч ${sortIcon('batch_number')}</th>
                            <th class="sortable" data-col="supplier_name" style="cursor:pointer">Поставщик ${sortIcon('supplier_name')}</th>
                            <th class="sortable" data-col="supplier_email" style="cursor:pointer">Email ${sortIcon('supplier_email')}</th>
                            <th class="sortable" data-col="email_status" style="cursor:pointer">Статус ${sortIcon('email_status')}</th>
                            <th class="sortable" data-col="sent_at" style="cursor:pointer">Отправлено ${sortIcon('sent_at')}</th>
                            <th class="sortable" data-col="clicked_at" style="cursor:pointer">Клик ${sortIcon('clicked_at')}</th>
                            <th class="sortable" data-col="error_message" style="cursor:pointer">Ошибка ${sortIcon('error_message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtered.length === 0 ? '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">Нет записей</td></tr>' : ''}
                        ${filtered.map(l => `
                            <tr>
                                <td style="text-align:center;font-weight:600">#${l.batch_number}</td>
                                <td style="font-weight:500">${l.supplier_name}</td>
                                <td style="color:var(--primary);font-size:12px">${l.supplier_email}</td>
                                <td>${badge(l.email_status)}</td>
                                <td style="color:var(--text-muted);font-size:12px;white-space:nowrap">${formatDate(l.sent_at)}</td>
                                <td style="font-size:12px;white-space:nowrap">${l.clicked_at ? '<span style="color:var(--success)">✓ ' + formatDate(l.clicked_at) + '</span>' : '<span style="color:var(--text-muted)">—</span>'}</td>
                                <td style="color:var(--danger);font-size:12px;max-width:180px;overflow:hidden;text-overflow:ellipsis" title="${l.error_message}">${l.error_message || '—'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // Sort handlers
        document.querySelectorAll('.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.col;
                if (sortColumn === col) {
                    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    sortColumn = col;
                    sortDir = 'asc';
                }
                render();
            });
        });

        // Filter handlers
        document.getElementById('bl-status-filter').addEventListener('change', (e) => {
            filterStatus = e.target.value;
            render();
        });
        document.getElementById('bl-batch-filter').addEventListener('change', (e) => {
            filterBatch = e.target.value;
            render();
        });
        document.getElementById('bl-search').addEventListener('input', (e) => {
            filterText = e.target.value;
            render();
        });
    }

    render();
}

// ── Pagination Helper ──
function renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container || totalPages <= 1) return;

    let html = `<button ${currentPage <= 1 ? 'disabled' : ''} data-page="${currentPage - 1}">←</button>`;

    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);

    for (let i = start; i <= end; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    html += `<button ${currentPage >= totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">→</button>`;
    container.innerHTML = html;

    container.querySelectorAll('button[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = parseInt(btn.dataset.page);
            if (page >= 1 && page <= totalPages) onPageChange(page);
        });
    });
}


// ═══════════════════════════════════════════════════
//  PAGE: SMTP Accounts
// ═══════════════════════════════════════════════════
async function renderSmtp(container) {
    let accounts = [];
    try {
        accounts = await api.get('/api/smtp-accounts');
    } catch (e) {
        accounts = [];
    }

    function formatDate(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }

    container.innerHTML = `
        <div class="card mb-24" style="padding:20px">
            <h3 style="margin:0 0 8px;font-size:16px">Ротация SMTP-аккаунтов</h3>
            <p style="margin:0;color:var(--text-muted);font-size:13px">
                Система отправляет письма по очереди с разных аккаунтов (round-robin). Если один попадёт в спам, остальные продолжат работу.<br>
                Если аккаунтов нет — используются данные из .env файла.
            </p>
        </div>

        <div class="card mb-24" style="padding:20px">
            <h3 style="margin:0 0 16px;font-size:15px">Добавить SMTP-аккаунт</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr 80px 80px auto;gap:8px;align-items:end">
                <div>
                    <label style="font-size:12px;color:var(--text-muted)">Email</label>
                    <input class="form-input" type="text" id="smtp-email" placeholder="user@domain.ru" style="height:36px;font-size:13px">
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted)">Пароль</label>
                    <input class="form-input" type="password" id="smtp-pass" placeholder="••••" style="height:36px;font-size:13px">
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted)">SMTP Host</label>
                    <input class="form-input" type="text" id="smtp-host" value="smtp.mail.ru" style="height:36px;font-size:13px">
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted)">Порт</label>
                    <input class="form-input" type="number" id="smtp-port" value="465" style="height:36px;font-size:13px">
                </div>
                <div>
                    <label style="font-size:12px;color:var(--text-muted)">TLS</label>
                    <select class="filter-select" id="smtp-tls" style="height:36px">
                        <option value="true" selected>Да</option>
                        <option value="false">Нет</option>
                    </select>
                </div>
                <button class="btn btn-primary" id="btn-add-smtp" style="height:36px;white-space:nowrap;gap:4px">
                    <span class="material-symbols-outlined" style="font-size:18px">add</span> Добавить
                </button>
            </div>
        </div>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>SMTP Host</th>
                        <th>Порт</th>
                        <th>TLS</th>
                        <th>Отправок</th>
                        <th>Последняя</th>
                        <th>Активен</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    ${accounts.length === 0 ? '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted)">Нет SMTP-аккаунтов. Используются данные из .env</td></tr>' : ''}
                    ${accounts.map(a => `
                        <tr>
                            <td style="font-weight:600;color:var(--primary)">${a.email}</td>
                            <td>${a.smtp_host}</td>
                            <td style="text-align:center">${a.smtp_port}</td>
                            <td style="text-align:center">${a.use_tls ? '✓' : '—'}</td>
                            <td style="text-align:center;font-weight:600">${a.send_count}</td>
                            <td style="font-size:12px;color:var(--text-muted)">${formatDate(a.last_used_at)}</td>
                            <td style="text-align:center">
                                <button class="btn smtp-toggle" data-id="${a.id}" data-active="${a.active}" style="padding:4px 12px;font-size:12px;background:${a.active ? 'var(--success)' : 'var(--danger)'};color:#fff;border:none;border-radius:6px;cursor:pointer">
                                    ${a.active ? 'Вкл' : 'Выкл'}
                                </button>
                            </td>
                            <td>
                                <button class="btn smtp-delete" data-id="${a.id}" style="padding:4px 8px;color:var(--danger);background:none;border:1px solid var(--danger);border-radius:6px;cursor:pointer;font-size:12px">
                                    <span class="material-symbols-outlined" style="font-size:16px">delete</span>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    // Add handler
    document.getElementById('btn-add-smtp').addEventListener('click', async () => {
        const email = document.getElementById('smtp-email').value.trim();
        const password = document.getElementById('smtp-pass').value.trim();
        const smtp_host = document.getElementById('smtp-host').value.trim();
        const smtp_port = parseInt(document.getElementById('smtp-port').value) || 465;
        const use_tls = document.getElementById('smtp-tls').value === 'true';

        if (!email || !password) {
            showToast('Введите email и пароль', 'error');
            return;
        }

        try {
            await api.post('/api/smtp-accounts', { email, password, smtp_host, smtp_port, use_tls });
            showToast('SMTP-аккаунт добавлен', 'success');
            renderSmtp(container);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    // Toggle handlers
    document.querySelectorAll('.smtp-toggle').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.dataset.id;
            const newActive = btn.dataset.active !== 'true';
            try {
                await api.put(`/api/smtp-accounts/${id}`, { active: newActive });
                showToast(newActive ? 'Аккаунт включён' : 'Аккаунт выключен', 'success');
                renderSmtp(container);
            } catch (e) {
                showToast('Ошибка: ' + e.message, 'error');
            }
        });
    });

    // Delete handlers
    document.querySelectorAll('.smtp-delete').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (!confirm('Удалить этот SMTP-аккаунт?')) return;
            try {
                await api.del(`/api/smtp-accounts/${btn.dataset.id}`);
                showToast('Аккаунт удалён', 'success');
                renderSmtp(container);
            } catch (e) {
                showToast('Ошибка: ' + e.message, 'error');
            }
        });
    });
}


// ═══════════════════════════════════════════════════
//  PAGE: Bid Search Results
// ═══════════════════════════════════════════════════
async function renderBidSearch(container, bidId) {
    const data = await api.get(`/api/bids/${bidId}/search-results`);
    const bid = data.bid;
    const results = data.results;

    function fmtDate(d) {
        if (!d) return '—';
        const dt = new Date(d);
        return dt.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' + dt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }

    // Group results by priority for summary
    const priorityGroups = {};
    results.forEach(r => {
        if (!priorityGroups[r.priority]) priorityGroups[r.priority] = [];
        priorityGroups[r.priority].push(r);
    });

    container.innerHTML = `
        <a href="#/bids" class="btn btn-sm btn-secondary mb-24" style="display:inline-flex;gap:4px;text-decoration:none">
            <span class="material-symbols-outlined" style="font-size:16px">arrow_back</span> Назад к заявкам
        </a>

        <!-- Bid Info Card -->
        <div class="card mb-24" style="padding:20px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
                <div>
                    <h3 style="margin:0 0 8px;font-size:17px">🔍 Заявка №${bid.source_id}: ${bid.name}</h3>
                    <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--text-muted)">
                        ${bid.brand ? `<span>🏭 <strong>${bid.brand} ${bid.model || ''}</strong>${bid.year ? ' (' + bid.year + ')' : ''}</span>` : ''}
                        ${bid.spare_part_type ? `<span>🔧 ${bid.spare_part_type}</span>` : ''}
                        ${bid.delivery_place ? `<span>📍 ${bid.delivery_place}</span>` : ''}
                        ${bid.part_number ? `<span>🏷️ Артикул: <strong>${bid.part_number}</strong></span>` : ''}
                    </div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:28px;font-weight:800;color:var(--primary)">${results.length}</div>
                    <div style="font-size:12px;color:var(--text-muted)">поставщиков найдено</div>
                </div>
            </div>
        </div>

        <!-- Priority Legend -->
        <div class="card mb-24" style="padding:16px">
            <h4 style="margin:0 0 10px;font-size:14px;color:var(--text-muted)">Приоритеты поиска</h4>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
                ${data.priority_legend.map(p => {
        const count = (priorityGroups[p.priority] || []).length;
        return `<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;background:${p.color}15;border:1px solid ${p.color}40;border-radius:6px;font-size:12px">
                        <span style="width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
                        ${p.label}
                        ${count > 0 ? `<strong style="color:${p.color}">(${count})</strong>` : ''}
                    </span>`;
    }).join('')}
            </div>
        </div>

        <!-- Results Table -->
        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Приоритет</th>
                        <th>Компания</th>
                        <th>Email</th>
                        <th>Категории</th>
                        <th>Регион</th>
                        <th>Отправка</th>
                        <th>Клик</th>
                    </tr>
                </thead>
                <tbody>
                    ${results.length === 0 ? '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">Нет результатов поиска. Рассылка ещё не проводилась.</td></tr>' : ''}
                    ${results.map(r => `
                        <tr>
                            <td>
                                <span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:${r.priority_color}20;color:${r.priority_color};border-radius:4px;font-size:11px;font-weight:700;white-space:nowrap">
                                    <span style="width:6px;height:6px;border-radius:50%;background:${r.priority_color}"></span>
                                    P${r.priority}
                                </span>
                            </td>
                            <td style="font-weight:600">
                                ${r.website ? `<a href="${r.website.startsWith('http') ? r.website : 'https://' + r.website}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none">${r.company_name} <span class="material-symbols-outlined" style="font-size:12px;vertical-align:middle;opacity:0.5">open_in_new</span></a>` : r.company_name}
                                ${r.source === 'ai' ? '<span style="font-size:10px;background:#8b5cf620;color:#8b5cf6;padding:1px 4px;border-radius:3px;margin-left:4px">AI</span>' : ''}
                            </td>
                            <td style="font-size:12px;color:var(--primary)">${r.email}</td>
                            <td style="font-size:11px">${(r.categories || []).map(c => `<span class="badge pending" style="font-size:10px;padding:1px 6px">${c}</span>`).join(' ') || '—'}</td>
                            <td style="font-size:12px;color:var(--text-muted)">${(r.regions || []).join(', ') || '—'}</td>
                            <td>
                                ${r.email_status === 'sent' ? `<span style="color:var(--success)" title="${fmtDate(r.sent_at)}">✓ ${fmtDate(r.sent_at).split(' ')[0]}</span>`
            : r.email_status === 'failed' ? '<span style="color:var(--danger)">✗ Ошибка</span>'
                : '<span style="color:var(--text-muted)">—</span>'}
                            </td>
                            <td>
                                ${r.clicked_at ? `<span style="color:var(--success);font-weight:600" title="${fmtDate(r.clicked_at)}">✓ Кликнул</span>`
            : '<span style="color:var(--text-muted)">—</span>'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ═══════════════════════════════════════════════════
//  PAGE: Campaigns (Manual Newsletters)
// ═══════════════════════════════════════════════════
async function renderCampaigns(container) {
    const data = await api.get('/api/campaigns');

    function campaignBadge(status) {
        const map = {
            draft: ['badge pending', 'Черновик'],
            sending: ['badge distributing', 'Отправка'],
            paused: ['badge waiting', 'Пауза'],
            completed: ['badge fully_notified', 'Завершена'],
            cancelled: ['badge expired', 'Отменена'],
        };
        const [cls, label] = map[status] || ['badge pending', status];
        return `<span class="${cls}">${label}</span>`;
    }

    function fmtDate(d) {
        if (!d) return '—';
        return new Date(d).toLocaleDateString('ru-RU', {day:'2-digit', month:'2-digit', year:'numeric'});
    }

    container.innerHTML = `
        <div class="action-bar">
            <div></div>
            <button class="btn btn-primary" id="btn-new-campaign">
                <span class="material-symbols-outlined">add</span> Новая рассылка
            </button>
        </div>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Тема</th>
                        <th>Статус</th>
                        <th>Получателей</th>
                        <th>Отправлено</th>
                        <th>Открыто</th>
                        <th>Ошибок</th>
                        <th>Дата</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.items.length === 0 ? '<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--text-muted)">Нет кампаний. Создайте первую рассылку.</td></tr>' : ''}
                    ${data.items.map(c => `
                        <tr style="cursor:pointer" onclick="location.hash='#/campaigns/${c.id}'">
                            <td style="font-weight:600;color:var(--primary)">${c.name}</td>
                            <td style="font-size:12px;color:var(--text-secondary)">${c.subject || '—'}</td>
                            <td>${campaignBadge(c.status)}</td>
                            <td style="text-align:center">${c.total_recipients}</td>
                            <td style="text-align:center;color:var(--success)">${c.sent_count}</td>
                            <td style="text-align:center">${c.opened_count}</td>
                            <td style="text-align:center;color:${c.failed_count > 0 ? 'var(--danger)' : 'var(--text-muted)'}">${c.failed_count}</td>
                            <td style="font-size:11px;color:var(--text-muted)">${fmtDate(c.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById('btn-new-campaign').addEventListener('click', () => {
        showCampaignModal(container);
    });
}


function showCampaignModal(container) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal" style="max-width:640px">
            <div class="modal-header">
                <h3>Новая рассылка</h3>
                <button class="modal-close" id="close-campaign-modal"><span class="material-symbols-outlined">close</span></button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Название кампании</label>
                    <input class="form-input" id="camp-name" placeholder="Например: Акция март 2026">
                </div>
                <div class="form-group">
                    <label class="form-label">Тема письма</label>
                    <input class="form-input" id="camp-subject" placeholder="Тема, которую увидит получатель">
                </div>
                <div class="form-group">
                    <label class="form-label">Тело письма (HTML)</label>
                    <textarea class="form-input" id="camp-body" rows="8" placeholder="<h1>Заголовок</h1><p>Текст письма...</p>" style="font-family:monospace;font-size:11px"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Получатели (по одному на строку)</label>
                    <textarea class="form-input" id="camp-recipients" rows="5" placeholder="email1@example.com&#10;email2@example.com&#10;email3@example.com"></textarea>
                    <p class="form-hint">Также принимает через запятую, точку с запятой или пробел</p>
                </div>
                <div class="form-group">
                    <label class="form-label">Интервал между письмами: <strong id="delay-val">30</strong> сек</label>
                    <input type="range" class="range-slider" id="camp-delay" min="10" max="300" value="30" step="10">
                    <div class="range-labels">
                        <span>10 сек</span>
                        <span class="center" id="delay-center">30 сек</span>
                        <span>300 сек</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" id="cancel-campaign">Отмена</button>
                <button class="btn btn-primary" id="save-campaign">Создать рассылку</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    const delaySlider = overlay.querySelector('#camp-delay');
    const delayVal = overlay.querySelector('#delay-val');
    const delayCenter = overlay.querySelector('#delay-center');
    delaySlider.addEventListener('input', () => {
        delayVal.textContent = delaySlider.value;
        delayCenter.textContent = delaySlider.value + ' сек';
    });

    overlay.querySelector('#close-campaign-modal').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-campaign').addEventListener('click', () => overlay.remove());

    overlay.querySelector('#save-campaign').addEventListener('click', async () => {
        const name = overlay.querySelector('#camp-name').value.trim();
        const subject = overlay.querySelector('#camp-subject').value.trim();
        const html_body = overlay.querySelector('#camp-body').value;
        const recipients = overlay.querySelector('#camp-recipients').value;
        const delay_seconds = parseInt(delaySlider.value);

        if (!name) { showToast('Укажите название', 'error'); return; }
        if (!subject) { showToast('Укажите тему письма', 'error'); return; }

        try {
            const result = await api.post('/api/campaigns', { name, subject, html_body, recipients, delay_seconds });
            showToast(result.message, 'success');
            overlay.remove();
            navigateTo(`/campaigns/${result.id}`);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });
}


async function renderCampaignDetail(container, campaignId) {
    const data = await api.get(`/api/campaigns/${campaignId}`);

    function fmtDate(d) {
        if (!d) return '—';
        const dt = new Date(d);
        return dt.toLocaleDateString('ru-RU', {day:'2-digit',month:'2-digit',year:'numeric'}) + ' ' + dt.toLocaleTimeString('ru-RU', {hour:'2-digit',minute:'2-digit'});
    }

    const total = data.total_recipients || 1;
    const processed = (data.sent_count || 0) + (data.failed_count || 0);
    const progress = Math.round(processed / total * 100);
    const openRate = data.sent_count > 0 ? Math.round(data.opened_count / data.sent_count * 100) : 0;

    function recipBadge(status) {
        const map = {
            pending: ['badge pending', '⏳ Ожидает'],
            sent: ['badge sent', '✓ Отправлено'],
            failed: ['badge failed', '✗ Ошибка'],
            opened: ['badge new', '👁 Открыто'],
            clicked: ['badge fully_notified', '🔗 Кликнул'],
        };
        const [cls, label] = map[status] || ['badge pending', status];
        return `<span class="${cls}">${label}</span>`;
    }

    container.innerHTML = `
        <a href="#/campaigns" class="btn btn-sm btn-secondary mb-24" style="display:inline-flex;gap:4px;text-decoration:none">
            <span class="material-symbols-outlined" style="font-size:14px">arrow_back</span> Назад
        </a>

        <!-- Campaign Header -->
        <div class="card mb-16" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                <div>
                    <h3 style="margin:0;font-size:15px">${data.name}</h3>
                    <p style="margin:2px 0 0;font-size:12px;color:var(--text-muted)">Тема: ${data.subject}</p>
                </div>
                <div style="display:flex;gap:6px" id="campaign-controls">
                    ${data.status === 'draft' ? `
                        <button class="btn btn-primary btn-sm" id="btn-send">
                            <span class="material-symbols-outlined" style="font-size:14px">send</span> Запустить
                        </button>
                        <button class="btn btn-secondary btn-sm" id="btn-test">
                            <span class="material-symbols-outlined" style="font-size:14px">science</span> Тест
                        </button>
                    ` : ''}
                    ${data.status === 'sending' ? `
                        <button class="btn btn-secondary btn-sm" id="btn-pause">
                            <span class="material-symbols-outlined" style="font-size:14px">pause</span> Пауза
                        </button>
                        <button class="btn btn-danger btn-sm" id="btn-cancel">
                            <span class="material-symbols-outlined" style="font-size:14px">stop</span> Отмена
                        </button>
                    ` : ''}
                    ${data.status === 'paused' ? `
                        <button class="btn btn-primary btn-sm" id="btn-resume">
                            <span class="material-symbols-outlined" style="font-size:14px">play_arrow</span> Продолжить
                        </button>
                        <button class="btn btn-danger btn-sm" id="btn-cancel">
                            <span class="material-symbols-outlined" style="font-size:14px">stop</span> Отмена
                        </button>
                    ` : ''}
                </div>
            </div>
        </div>

        <!-- Progress -->
        <div class="card mb-16" style="padding:14px">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-bottom:4px">
                <span>Прогресс: ${processed} / ${data.total_recipients}</span>
                <span>${progress}%</span>
            </div>
            <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden">
                <div style="height:100%;width:${progress}%;background:var(--primary);border-radius:3px;transition:width 0.3s"></div>
            </div>
        </div>

        <!-- Stats -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Отправлено</div>
                <div class="kpi-value" style="color:var(--success)">${data.sent_count}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Открыто (${openRate}%)</div>
                <div class="kpi-value" style="color:var(--info)">${data.opened_count}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Кликнуло</div>
                <div class="kpi-value" style="color:var(--primary)">${data.clicked_count}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Ошибок</div>
                <div class="kpi-value" style="color:var(--danger)">${data.failed_count}</div>
            </div>
        </div>

        <!-- Attachments -->
        ${data.attachments.length > 0 ? `
            <div class="card mb-16" style="padding:10px 14px">
                <div style="font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:6px">Вложения</div>
                ${data.attachments.map(a => `
                    <span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;background:var(--bg-input);border-radius:3px;font-size:11px;margin-right:4px">
                        <span class="material-symbols-outlined" style="font-size:13px">attach_file</span>
                        ${a.filename} (${Math.round(a.size_bytes/1024)} КБ)
                    </span>
                `).join('')}
            </div>
        ` : ''}

        ${data.status === 'draft' ? `
            <div class="card mb-16" style="padding:10px 14px">
                <div style="font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin-bottom:6px">Прикрепить файл</div>
                <input type="file" id="att-file" style="font-size:12px">
                <button class="btn btn-sm btn-secondary" id="btn-upload" style="margin-left:8px">Загрузить</button>
            </div>
        ` : ''}

        <!-- Recipients Table -->
        <div class="card">
            <div class="card-header">
                <h3>Получатели (${data.recipients.length})</h3>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Статус</th>
                        <th>Отправлено</th>
                        <th>Открыто</th>
                        <th>Клик</th>
                        <th>Ошибка</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.recipients.map(r => `
                        <tr>
                            <td style="font-size:12px">${r.email}</td>
                            <td>${recipBadge(r.status)}</td>
                            <td style="font-size:11px;color:var(--text-muted)">${fmtDate(r.sent_at)}</td>
                            <td style="font-size:11px">${r.opened_at ? `<span style="color:var(--success)">✓ ${fmtDate(r.opened_at).split(' ')[1]}</span>` : '—'}</td>
                            <td style="font-size:11px">${r.clicked_at ? `<span style="color:var(--success);font-weight:600">✓</span>` : '—'}</td>
                            <td style="font-size:10px;color:var(--danger)">${r.error_message || ''}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    // Event handlers
    const btnSend = container.querySelector('#btn-send');
    if (btnSend) {
        btnSend.addEventListener('click', async () => {
            if (!confirm(`Запустить рассылку "${data.name}" на ${data.total_recipients} получателей?`)) return;
            try {
                await api.post(`/api/campaigns/${campaignId}/send`);
                showToast('Рассылка запущена!', 'success');
                renderCampaignDetail(container, campaignId);
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    const btnPause = container.querySelector('#btn-pause');
    if (btnPause) {
        btnPause.addEventListener('click', async () => {
            try {
                await api.post(`/api/campaigns/${campaignId}/pause`);
                showToast('Рассылка приостановлена', 'info');
                renderCampaignDetail(container, campaignId);
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    const btnResume = container.querySelector('#btn-resume');
    if (btnResume) {
        btnResume.addEventListener('click', async () => {
            try {
                await api.post(`/api/campaigns/${campaignId}/resume`);
                showToast('Рассылка возобновлена', 'success');
                renderCampaignDetail(container, campaignId);
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    const btnCancel = container.querySelector('#btn-cancel');
    if (btnCancel) {
        btnCancel.addEventListener('click', async () => {
            if (!confirm('Отменить рассылку?')) return;
            try {
                await api.post(`/api/campaigns/${campaignId}/cancel`);
                showToast('Рассылка отменена', 'info');
                renderCampaignDetail(container, campaignId);
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    const btnTest = container.querySelector('#btn-test');
    if (btnTest) {
        btnTest.addEventListener('click', async () => {
            const email = prompt('Email для тестового письма:');
            if (!email) return;
            try {
                const result = await api.post(`/api/campaigns/${campaignId}/test`, { email });
                showToast(result.message, 'success');
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    const btnUpload = container.querySelector('#btn-upload');
    if (btnUpload) {
        btnUpload.addEventListener('click', async () => {
            const fileInput = container.querySelector('#att-file');
            if (!fileInput.files.length) { showToast('Выберите файл', 'error'); return; }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            try {
                const resp = await fetch(`/api/campaigns/${campaignId}/attachments`, { method: 'POST', body: formData });
                if (!resp.ok) throw new Error((await resp.json()).detail);
                showToast('Файл загружен', 'success');
                renderCampaignDetail(container, campaignId);
            } catch (e) { showToast(e.message, 'error'); }
        });
    }

    // Auto-refresh while sending
    if (data.status === 'sending') {
        setTimeout(() => renderCampaignDetail(container, campaignId), 5000);
    }
}

// ══════════════════════════════════════════
//  MONITORING PAGE
// ══════════════════════════════════════════

function monitorStatusIcon(status) {
    const map = {
        pass: '<span class="material-symbols-outlined" style="color:var(--success)">check_circle</span>',
        fail: '<span class="material-symbols-outlined" style="color:var(--danger)">cancel</span>',
        error: '<span class="material-symbols-outlined" style="color:var(--danger)">error</span>',
        skip: '<span class="material-symbols-outlined" style="color:var(--text-muted)">remove_circle</span>',
        unknown: '<span class="material-symbols-outlined" style="color:var(--text-muted)">help</span>',
        running: '<span class="material-symbols-outlined spin-slow" style="color:var(--primary)">sync</span>',
    };
    return map[status] || map.unknown;
}

function monitorBadge(status) {
    const labels = { pass: 'OK', fail: 'FAIL', error: 'ERR', skip: 'SKIP', unknown: '—', running: '...' };
    const colors = { pass: '#059669', fail: '#dc2626', error: '#dc2626', skip: '#6b7280', unknown: '#6b7280', running: '#2563eb' };
    return `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;letter-spacing:0.5px;color:#fff;background:${colors[status]||'#6b7280'}">${labels[status]||status}</span>`;
}

function monitorHealthColor(status) {
    return status === 'healthy' ? 'var(--success)' : status === 'warning' ? 'var(--warning)' : 'var(--danger)';
}

async function renderMonitor(container) {
    container.innerHTML = '<div class="spinner"></div>';

    try {
        const [statusData, testsData, runsData] = await Promise.all([
            api.get('/api/monitor/status'),
            api.get('/api/monitor/tests'),
            api.get('/api/monitor/runs?limit=10'),
        ]);

        const health = statusData.status || 'unknown';
        const lr = statusData.last_run;

        container.innerHTML = `
        <div class="monitor-page">
            <!-- Health Banner -->
            <div class="monitor-health" style="background:${monitorHealthColor(health)}15;border:1px solid ${monitorHealthColor(health)}40;border-radius:8px;padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;gap:12px">
                <span class="material-symbols-outlined" style="font-size:32px;color:${monitorHealthColor(health)}">${health==='healthy'?'verified':health==='warning'?'warning':'error'}</span>
                <div>
                    <div style="font-weight:600;font-size:15px;color:${monitorHealthColor(health)}">${health==='healthy'?'Все системы работают штатно':health==='warning'?'Обнаружены проблемы':'Критические сбои'}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Последний прогон: ${lr ? timeAgo(lr.started_at) : 'не проводился'}</div>
                </div>
                <div style="margin-left:auto;display:flex;gap:8px">
                    <button class="btn btn-sm ${statusData.is_running?'btn-disabled':'btn-primary'}" id="mon-run-btn" ${statusData.is_running?'disabled':''}>
                        <span class="material-symbols-outlined">${statusData.is_running?'sync':'play_arrow'}</span>
                        ${statusData.is_running?'Тесты идут...':'Запустить тесты'}
                    </button>
                </div>
            </div>

            <!-- Stats Cards -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px">
                <div class="stat-card" style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:700;color:var(--success)">${statusData.uptime_pct}%</div>
                    <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Uptime</div>
                </div>
                <div class="stat-card" style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:700;color:var(--primary)">${lr ? lr.duration_ms : 0}<span style="font-size:14px">ms</span></div>
                    <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Время прогона</div>
                </div>
                <div class="stat-card" style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:700;color:var(--success)">${lr ? lr.passed : 0}<span style="font-size:14px">/${lr ? lr.total : 0}</span></div>
                    <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Пройдено</div>
                </div>
                <div class="stat-card" style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:700;color:${lr&&lr.failed>0?'var(--danger)':'var(--text-muted)'}">${lr ? lr.failed : 0}</div>
                    <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Ошибки</div>
                </div>
                <div class="stat-card" style="text-align:center;padding:16px">
                    <div style="font-size:28px;font-weight:700;color:var(--text)">${statusData.total_runs}</div>
                    <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px">Всего прогонов</div>
                </div>
            </div>

            <!-- Tests Table -->
            <div class="card" style="margin-bottom:20px">
                <div class="card-header" style="display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--border)">
                    <span class="material-symbols-outlined" style="color:var(--primary)">checklist</span>
                    <span style="font-weight:600;font-size:14px">Тесты (${testsData.total})</span>
                    <div style="margin-left:auto;display:flex;gap:6px">
                        <button class="btn btn-sm btn-ghost" id="mon-filter-all">Все</button>
                        <button class="btn btn-sm btn-ghost" id="mon-filter-pass">✓ OK</button>
                        <button class="btn btn-sm btn-ghost" id="mon-filter-fail">✗ Fail</button>
                    </div>
                </div>
                <div style="overflow-x:auto">
                    <table class="table" id="mon-tests-table">
                        <thead>
                            <tr>
                                <th style="width:50px">Код</th>
                                <th>Тест</th>
                                <th style="width:70px">Группа</th>
                                <th style="width:70px">Статус</th>
                                <th style="width:80px">Время</th>
                                <th style="width:60px">HTTP</th>
                                <th>Ошибка</th>
                                <th style="width:40px"></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${testsData.tests.map(t => `
                                <tr data-status="${t.last_status}">
                                    <td><code style="font-size:11px;color:var(--primary)">${t.code}</code></td>
                                    <td style="font-size:13px">${t.name}</td>
                                    <td><span style="font-size:11px;color:var(--text-muted);text-transform:uppercase">${t.group}</span></td>
                                    <td>${monitorBadge(t.last_status)}</td>
                                    <td style="font-size:12px;color:var(--text-muted)">${t.last_duration_ms}ms</td>
                                    <td style="font-size:12px">${t.last_response_code||'—'}</td>
                                    <td style="font-size:12px;color:var(--danger);max-width:400px;white-space:normal;word-break:break-word;line-height:1.4" title="${(t.last_error||'').replace(/"/g,'&quot;')}">${t.last_error||''}</td>
                                    <td>
                                        <button class="btn btn-sm btn-ghost mon-rerun" data-id="${t.id}" title="Запустить">
                                            <span class="material-symbols-outlined" style="font-size:16px">replay</span>
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Run History -->
            <div class="card" style="margin-bottom:20px">
                <div class="card-header" style="display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--border)">
                    <span class="material-symbols-outlined" style="color:var(--primary)">history</span>
                    <span style="font-weight:600;font-size:14px">История прогонов</span>
                </div>
                <div style="padding:0">
                    ${runsData.runs.length === 0 ? '<div style="padding:24px;text-align:center;color:var(--text-muted)">Ещё не было прогонов</div>' : ''}
                    ${runsData.runs.map(r => `
                        <div class="mon-run-row" data-run-id="${r.id}" style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);cursor:pointer;transition:background 0.15s" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background=''">
                            ${monitorStatusIcon(r.failed > 0 ? 'fail' : 'pass')}
                            <div style="flex:1">
                                <div style="font-size:13px;font-weight:500">
                                    Прогон #${r.id}
                                    <span style="font-size:11px;color:var(--text-muted);margin-left:6px">${r.trigger === 'auto' ? '⏱ авто' : '👤 ручной'}</span>
                                </div>
                                <div style="font-size:11px;color:var(--text-muted)">${r.started_at ? new Date(r.started_at).toLocaleString('ru') : '—'}</div>
                            </div>
                            <div style="display:flex;gap:8px;align-items:center">
                                <span style="color:var(--success);font-weight:600;font-size:13px">${r.passed}</span>
                                <span style="color:var(--text-muted);font-size:11px">/</span>
                                <span style="color:${r.failed>0?'var(--danger)':'var(--text-muted)'};font-weight:600;font-size:13px">${r.failed}</span>
                                <span style="color:var(--text-muted);font-size:11px;margin-left:4px">${r.duration_ms}ms</span>
                            </div>
                            <span class="material-symbols-outlined" style="font-size:18px;color:var(--text-muted)">chevron_right</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Config -->
            <div class="card">
                <div class="card-header" style="display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--border)">
                    <span class="material-symbols-outlined" style="color:var(--primary)">settings</span>
                    <span style="font-weight:600;font-size:14px">Настройки</span>
                </div>
                <div style="padding:16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap">
                    <label style="font-size:13px;display:flex;align-items:center;gap:6px;cursor:pointer">
                        <input type="checkbox" id="mon-enabled" ${statusData.enabled?'checked':''}>
                        Автоматический мониторинг
                    </label>
                    <label style="font-size:13px;display:flex;align-items:center;gap:6px">
                        Интервал:
                        <input type="number" id="mon-interval" value="${statusData.interval_minutes}" min="5" max="1440" style="width:60px;padding:4px 6px;border:1px solid var(--border);border-radius:4px;font-size:13px">
                        мин.
                    </label>
                    <button class="btn btn-sm btn-primary" id="mon-save-config">Сохранить</button>
                </div>
            </div>

            <!-- Run detail modal -->
            <div id="mon-run-detail" style="display:none"></div>
        </div>
        `;

        // Event: Run all tests
        document.getElementById('mon-run-btn')?.addEventListener('click', async () => {
            try {
                await api.post('/api/monitor/run', {});
                showToast('Тесты запущены', 'success');
                setTimeout(() => renderMonitor(container), 3000);
            } catch (e) { showToast(e.message, 'error'); }
        });

        // Event: Single test rerun
        document.querySelectorAll('.mon-rerun').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                try {
                    const res = await api.post(`/api/monitor/run/${id}`, {});
                    showToast(`${res.code}: ${res.status === 'pass' ? 'OK ✓' : res.error_message || 'FAIL'}`, res.status === 'pass' ? 'success' : 'error');
                    renderMonitor(container);
                } catch (e) { showToast(e.message, 'error'); }
            });
        });

        // Event: Filter tests
        document.getElementById('mon-filter-all')?.addEventListener('click', () => {
            document.querySelectorAll('#mon-tests-table tbody tr').forEach(r => r.style.display = '');
        });
        document.getElementById('mon-filter-pass')?.addEventListener('click', () => {
            document.querySelectorAll('#mon-tests-table tbody tr').forEach(r => {
                r.style.display = r.dataset.status === 'pass' ? '' : 'none';
            });
        });
        document.getElementById('mon-filter-fail')?.addEventListener('click', () => {
            document.querySelectorAll('#mon-tests-table tbody tr').forEach(r => {
                r.style.display = ['fail','error'].includes(r.dataset.status) ? '' : 'none';
            });
        });

        // Event: Save config
        document.getElementById('mon-save-config')?.addEventListener('click', async () => {
            try {
                await api.put('/api/monitor/config', {
                    enabled: document.getElementById('mon-enabled').checked,
                    interval_minutes: parseInt(document.getElementById('mon-interval').value),
                });
                showToast('Настройки сохранены', 'success');
            } catch (e) { showToast(e.message, 'error'); }
        });

        // Event: View run details
        document.querySelectorAll('.mon-run-row').forEach(row => {
            row.addEventListener('click', async () => {
                const runId = row.dataset.runId;
                try {
                    const detail = await api.get(`/api/monitor/runs/${runId}`);
                    const modal = document.getElementById('mon-run-detail');
                    modal.style.display = 'block';
                    modal.innerHTML = `
                        <div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center" onclick="this.remove()">
                            <div style="background:var(--card-bg);border-radius:12px;padding:20px;max-width:700px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3)" onclick="event.stopPropagation()">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
                                    <span class="material-symbols-outlined" style="color:var(--primary)">assignment</span>
                                    <h3 style="font-size:16px;font-weight:600;margin:0">Прогон #${detail.run.id}</h3>
                                    <span style="font-size:12px;color:var(--text-muted);margin-left:auto">${new Date(detail.run.started_at).toLocaleString('ru')}</span>
                                    <button class="btn btn-sm btn-ghost" style="margin-left:8px" onclick="this.closest('[style*=fixed]').remove()">✕</button>
                                </div>
                                <div style="display:flex;gap:12px;margin-bottom:12px;font-size:13px">
                                    <span style="color:var(--success)">✓ ${detail.run.passed}</span>
                                    <span style="color:var(--danger)">✗ ${detail.run.failed}</span>
                                    <span style="color:var(--text-muted)">${detail.run.duration_ms}ms</span>
                                    <span style="color:var(--text-muted)">${detail.run.trigger}</span>
                                </div>
                                <table class="table" style="font-size:12px">
                                    <thead><tr><th>Код</th><th>Тест</th><th>Статус</th><th>Время</th><th>HTTP</th><th>Ошибка</th></tr></thead>
                                    <tbody>
                                        ${detail.results.map(r => `
                                            <tr>
                                                <td><code>${r.code}</code></td>
                                                <td>${r.name}</td>
                                                <td>${monitorBadge(r.status)}</td>
                                                <td>${r.duration_ms}ms</td>
                                                <td>${r.response_code||'—'}</td>
                                                <td style="color:var(--danger);max-width:300px;white-space:normal;word-break:break-word;line-height:1.4" title="${(r.error_message||'').replace(/"/g,'&quot;')}">${r.error_message||''}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                } catch (e) { showToast(e.message, 'error'); }
            });
        });

        // Auto-refresh if running
        if (statusData.is_running) {
            setTimeout(() => renderMonitor(container), 5000);
        }

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
    }
}

// ══════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    handleRoute();
    updateSystemStatus();
    setInterval(updateSystemStatus, 15000);
});
window.addEventListener('hashchange', handleRoute);
