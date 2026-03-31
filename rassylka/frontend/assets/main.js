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
    '/telegram': renderTelegram,
    '/reports': renderReports,
    '/promotion': renderPromotion,
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
    '/telegram': 'TG Рассылка',
    '/reports': 'Отчёты по переходам',
    '/promotion': 'Продвижение',
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

    // Check for TG campaign detail route: /telegram/123
    const tgCampaignMatch = route.match(/^\/telegram\/(\d+)$/);
    if (tgCampaignMatch) {
        const tgCampaignId = parseInt(tgCampaignMatch[1]);
        document.getElementById('page-title').textContent = 'Детали TG-кампании';
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === 'telegram');
        });
        const content = document.getElementById('content-area');
        content.innerHTML = '<div class="spinner"></div>';
        try {
            await renderTgCampaignDetail(content, tgCampaignId);
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

            <!-- Batching Logic: NEW 2-step scheme -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">reorder</span>
                    <h3>Логика пакетирования</h3>
                </div>
                <div class="card-body">
                    <p class="form-hint" style="margin-bottom:16px;padding:8px 12px;background:rgba(107,99,255,0.1);border-radius:6px;border-left:3px solid var(--primary)">
                        <strong>Схема:</strong> Батч 1 → пауза (эскалация) → Батч 2. Все параметры настраиваемые.
                    </p>
                    <h4 style="font-size:13px;color:var(--primary);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px">Батч 1 (первичная рассылка)</h4>
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">Кол-во писем</label>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch1-size" value="${rules.batch1_size || 5}" min="1" max="50">
                                <span class="suffix">писем</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Пауза между письмами</label>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch1-delay" value="${rules.batch1_delay_seconds || 120}" min="5" max="600">
                                <span class="suffix">секунд</span>
                            </div>
                        </div>
                    </div>
                    <div class="form-group" style="margin-top:12px">
                        <h4 style="font-size:13px;color:var(--warning);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px">⏳ Пауза между батчами</h4>
                        <div class="form-input-suffix" style="max-width:300px">
                            <input class="form-input" type="number" id="r-escalation-hours" value="${rules.escalation_hours || 24}" min="1" max="168">
                            <span class="suffix">часов</span>
                        </div>
                        <p class="form-hint">Если нет откликов после батча 1 — ждём указанное время.</p>
                    </div>
                    <h4 style="font-size:13px;color:var(--success);margin-top:16px;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px">Батч 2 (эскалация)</h4>
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">Кол-во писем</label>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch2-size" value="${rules.batch2_size || 10}" min="1" max="100">
                                <span class="suffix">писем</span>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Пауза между письмами</label>
                            <div class="form-input-suffix">
                                <input class="form-input" type="number" id="r-batch2-delay" value="${rules.batch2_delay_seconds || 120}" min="5" max="600">
                                <span class="suffix">секунд</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Supplier Archiving -->
            <div class="card mb-24">
                <div class="section-header">
                    <span class="material-symbols-outlined">archive</span>
                    <h3>Архивация неактивных поставщиков</h3>
                </div>
                <div class="card-body">
                    <div class="form-group">
                        <label class="form-label">Макс. писем без ответа</label>
                        <p class="form-hint">После N писем без кликов с разных SMTP — поставщик автоматически архивируется.</p>
                        <div class="form-input-suffix" style="max-width:300px">
                            <input class="form-input" type="number" id="r-max-no-response" value="${rules.max_no_response || 10}" min="3" max="100">
                            <span class="suffix">писем</span>
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
                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                        <input type="checkbox" id="r-auto-supplier-search" ${rules.auto_supplier_search !== false ? 'checked' : ''} style="width:18px;height:18px;accent-color:var(--primary)">
                        <div>
                            <span style="font-size:14px;font-weight:600">Автопоиск поставщиков</span>
                            <p style="font-size:12px;color:var(--text-muted)">AI автоматически ищет новых поставщиков по категориям заявок (раз в сутки)</p>
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
                matching_sensitivity: parseInt(document.getElementById('r-sensitivity').value) / 100,
                filter_keywords: keywords,
                auto_parse: document.getElementById('r-auto-parse').checked,
                auto_distribute: document.getElementById('r-auto-distribute').checked,
                auto_supplier_search: document.getElementById('r-auto-supplier-search').checked,
                parse_interval_minutes: parseInt(document.getElementById('r-parse-interval').value),
                email_delay_seconds: parseInt(document.getElementById('r-email-delay').value),
                batch1_size: parseInt(document.getElementById('r-batch1-size').value),
                batch1_delay_seconds: parseInt(document.getElementById('r-batch1-delay').value),
                batch2_size: parseInt(document.getElementById('r-batch2-size').value),
                batch2_delay_seconds: parseInt(document.getElementById('r-batch2-delay').value),
                escalation_hours: parseInt(document.getElementById('r-escalation-hours').value),
                max_no_response: parseInt(document.getElementById('r-max-no-response').value),
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
                        <option value="clicked" ${filterStatus === 'clicked' ? 'selected' : ''}>Перешёл</option>
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
                            <th style="min-width:200px">Статус доставки</th>
                            <th class="gl-sort" data-col="sent_at" style="cursor:pointer">Отправлено ${sortIcon('sent_at')}</th>
                            <th class="gl-sort" data-col="error_message" style="cursor:pointer">Ошибка ${sortIcon('error_message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtered.length === 0 ? '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">Нет записей в логе</td></tr>' : ''}
                        ${filtered.map(log => `
                            <tr>
                                <td style="font-weight:500">
                                    <a href="#/bids/${log.bid_id}/logs" style="color:var(--primary);text-decoration:none;font-weight:600" title="Открыть логи заявки">UM-${log.bid_source_id}</a>
                                    <br><span style="font-size:11px;color:var(--text-muted);max-width:150px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${log.bid_name}</span>
                                </td>
                                <td style="font-weight:500">${log.supplier_website ? `<a href="${log.supplier_website.startsWith('http') ? log.supplier_website : 'https://' + log.supplier_website}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none" title="${log.supplier_website}">${log.supplier_name} <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;opacity:0.5">open_in_new</span></a>` : log.supplier_name}</td>
                                <td style="color:var(--primary);font-size:12px">${log.supplier_email}</td>
                                <td style="text-align:center;font-weight:600">#${log.batch_number}</td>
                                <td>
                                    <div style="display:flex;align-items:center;gap:4px">
                                        <span title="${log.email_status === 'sent' || log.opened_at || log.clicked_at ? '✅ Доставлено: ' + (log.sent_at ? new Date(log.sent_at).toLocaleString('ru') : '') : '❌ Не доставлено: ' + (log.error_message || '')}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${log.email_status === 'sent' || log.opened_at || log.clicked_at ? 'background:#10b98114;color:#10b981' : 'background:#ef444414;color:#ef4444'}"><span class="material-symbols-outlined" style="font-size:14px">${log.email_status === 'failed' ? 'error' : 'mark_email_read'}</span>Доставл.</span>
                                        <span style="color:var(--text-muted)">→</span>
                                        <span title="${log.opened_at ? '✅ Открыто: ' + new Date(log.opened_at).toLocaleString('ru') : '⏳ Не открыто'}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${log.opened_at ? 'background:#8b5cf614;color:#8b5cf6' : 'background:var(--bg-secondary);color:var(--text-muted)'}">
                                            <span class="material-symbols-outlined" style="font-size:14px">${log.opened_at ? 'visibility' : 'visibility_off'}</span>Открыл</span>
                                        <span style="color:var(--text-muted)">→</span>
                                        <span title="${log.clicked_at ? '✅ Перешёл: ' + new Date(log.clicked_at).toLocaleString('ru') : '⏳ Не перешёл'}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${log.clicked_at ? 'background:#f59e0b14;color:#f59e0b' : 'background:var(--bg-secondary);color:var(--text-muted)'}">
                                            <span class="material-symbols-outlined" style="font-size:14px">${log.clicked_at ? 'ads_click' : 'do_not_touch'}</span>Перешёл</span>
                                    </div>
                                </td>
                                <td style="color:var(--text-muted);font-size:12px;white-space:nowrap">${formatDate(log.sent_at)}</td>
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
                        <option value="clicked" ${filterStatus === 'clicked' ? 'selected' : ''}>Перешёл</option>
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
                            <th style="min-width:200px">Статус доставки</th>
                            <th class="sortable" data-col="sent_at" style="cursor:pointer">Отправлено ${sortIcon('sent_at')}</th>
                            <th class="sortable" data-col="error_message" style="cursor:pointer">Ошибка ${sortIcon('error_message')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtered.length === 0 ? '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted)">Нет записей</td></tr>' : ''}
                        ${filtered.map(l => `
                            <tr>
                                <td style="text-align:center;font-weight:600">#${l.batch_number}</td>
                                <td style="font-weight:500">${l.supplier_website ? `<a href="${l.supplier_website.startsWith('http') ? l.supplier_website : 'https://' + l.supplier_website}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none" title="${l.supplier_website}">${l.supplier_name} <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;opacity:0.5">open_in_new</span></a>` : l.supplier_name}</td>
                                <td style="color:var(--primary);font-size:12px">${l.supplier_email}</td>
                                <td>
                                    <div style="display:flex;align-items:center;gap:4px">
                                        <span title="${l.email_status === 'sent' || l.opened_at || l.clicked_at ? '✅ Доставлено: ' + (l.sent_at ? new Date(l.sent_at).toLocaleString('ru') : '') : '❌ Не доставлено: ' + (l.error_message || '')}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${l.email_status === 'sent' || l.opened_at || l.clicked_at ? 'background:#10b98114;color:#10b981' : 'background:#ef444414;color:#ef4444'}"><span class="material-symbols-outlined" style="font-size:14px">${l.email_status === 'failed' ? 'error' : 'mark_email_read'}</span>Доставл.</span>
                                        <span style="color:var(--text-muted)">→</span>
                                        <span title="${l.opened_at ? '✅ Открыто: ' + new Date(l.opened_at).toLocaleString('ru') : '⏳ Не открыто'}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${l.opened_at ? 'background:#8b5cf614;color:#8b5cf6' : 'background:var(--bg-secondary);color:var(--text-muted)'}">
                                            <span class="material-symbols-outlined" style="font-size:14px">${l.opened_at ? 'visibility' : 'visibility_off'}</span>Открыл</span>
                                        <span style="color:var(--text-muted)">→</span>
                                        <span title="${l.clicked_at ? '✅ Перешёл: ' + new Date(l.clicked_at).toLocaleString('ru') : '⏳ Не перешёл'}" style="display:inline-flex;align-items:center;gap:2px;padding:3px 6px;border-radius:4px;font-size:11px;font-weight:600;${l.clicked_at ? 'background:#f59e0b14;color:#f59e0b' : 'background:var(--bg-secondary);color:var(--text-muted)'}">
                                            <span class="material-symbols-outlined" style="font-size:14px">${l.clicked_at ? 'ads_click' : 'do_not_touch'}</span>Перешёл</span>
                                    </div>
                                </td>
                                <td style="color:var(--text-muted);font-size:12px;white-space:nowrap">${formatDate(l.sent_at)}</td>
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
        <div class="modal" style="max-width:900px;max-height:92vh;display:flex;flex-direction:column">
            <div class="modal-header">
                <h3>Новая рассылка</h3>
                <button class="modal-close" id="close-campaign-modal"><span class="material-symbols-outlined">close</span></button>
            </div>
            <div class="modal-body" style="overflow-y:auto;flex:1">
                <div class="form-group">
                    <label class="form-label">Название кампании</label>
                    <input class="form-input" id="camp-name" placeholder="Например: Акция март 2026">
                </div>
                <div class="form-group">
                    <label class="form-label">Тема письма</label>
                    <input class="form-input" id="camp-subject" placeholder="Тема, которую увидит получатель">
                </div>

                <!-- Template Selector -->
                <div class="form-group">
                    <label class="form-label">Шаблон письма</label>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px" id="template-selector">
                        <label style="display:flex;align-items:center;gap:6px;padding:8px 14px;border:2px solid var(--primary);border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;background:rgba(107,99,255,0.08)">
                            <input type="radio" name="camp-template" value="umit" checked style="accent-color:var(--primary)">
                            <span class="material-symbols-outlined" style="font-size:16px;color:var(--primary)">verified</span>
                            Umit (по умолчанию)
                        </label>
                        <label style="display:flex;align-items:center;gap:6px;padding:8px 14px;border:2px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;font-weight:500" id="tpl-label-prom28-dvigateli">
                            <input type="radio" name="camp-template" value="prom28-dvigateli" style="accent-color:#d72710">
                            <span style="color:#d72710;font-weight:700">P28</span>
                            Двигатели
                        </label>
                        <label style="display:flex;align-items:center;gap:6px;padding:8px 14px;border:2px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;font-weight:500" id="tpl-label-prom28-pogruzchiki">
                            <input type="radio" name="camp-template" value="prom28-pogruzchiki" style="accent-color:#d72710">
                            <span style="color:#d72710;font-weight:700">P28</span>
                            Погрузчики
                        </label>
                        <label style="display:flex;align-items:center;gap:6px;padding:8px 14px;border:2px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;font-weight:500">
                            <input type="radio" name="camp-template" value="custom" style="accent-color:var(--warning)">
                            <span class="material-symbols-outlined" style="font-size:16px;color:var(--warning)">code</span>
                            Свой HTML
                        </label>
                    </div>
                </div>

                <!-- Umit content area (simple textarea) -->
                <div class="form-group" id="umit-body-area">
                    <div style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:6px">
                        <span class="material-symbols-outlined" style="font-size:14px;color:var(--success)">verified</span>
                        Автоматически оформляется в фирменном шаблоне Umit (логотип, шапка, мобильное приложение, футер)
                    </div>
                    <textarea class="form-input" id="camp-body" rows="8" placeholder="Здравствуйте!&#10;&#10;Приглашаем вас ознакомиться с новыми заявками на маркетплейсе Umit.&#10;&#10;С уважением,&#10;Команда Umit" style="font-size:13px;line-height:1.5"></textarea>
                    <p class="form-hint">Можно использовать HTML-теги для форматирования (&lt;b&gt;, &lt;br&gt;, &lt;p&gt;, &lt;ul&gt;)</p>
                </div>

                <!-- Visual HTML editor (for Prom28 / custom) -->
                <div class="form-group" id="html-editor-area" style="display:none">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                        <div style="font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:6px">
                            <span class="material-symbols-outlined" style="font-size:14px;color:#d72710">edit</span>
                            <span id="editor-mode-hint">Кликайте на текст для редактирования. Все изменения сохраняются.</span>
                        </div>
                        <div style="display:flex;gap:6px">
                            <button class="btn btn-sm btn-secondary" id="btn-visual-mode" style="font-size:11px;padding:4px 10px" disabled>
                                <span class="material-symbols-outlined" style="font-size:14px">visibility</span> Визуальный
                            </button>
                            <button class="btn btn-sm btn-secondary" id="btn-source-mode" style="font-size:11px;padding:4px 10px">
                                <span class="material-symbols-outlined" style="font-size:14px">code</span> Исходный код
                            </button>
                        </div>
                    </div>
                    <div id="visual-editor-wrap" style="border:1px solid var(--border);border-radius:8px;overflow:hidden;background:#fff">
                        <iframe id="visual-editor" style="width:100%;height:500px;border:none"></iframe>
                    </div>
                    <div id="source-editor-wrap" style="display:none">
                        <textarea class="form-input" id="source-editor" rows="20" style="font-family:monospace;font-size:11px;line-height:1.4;white-space:pre;tab-size:2"></textarea>
                    </div>
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

    // State
    let currentTemplate = 'umit';
    let templateHtmlCache = {};
    let isSourceMode = false;

    // Delay slider
    const delaySlider = overlay.querySelector('#camp-delay');
    const delayVal = overlay.querySelector('#delay-val');
    const delayCenter = overlay.querySelector('#delay-center');
    delaySlider.addEventListener('input', () => {
        delayVal.textContent = delaySlider.value;
        delayCenter.textContent = delaySlider.value + ' сек';
    });

    // Close handlers
    overlay.querySelector('#close-campaign-modal').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#cancel-campaign').addEventListener('click', () => overlay.remove());

    // Template selector
    const umitArea = overlay.querySelector('#umit-body-area');
    const htmlEditorArea = overlay.querySelector('#html-editor-area');
    const visualEditorWrap = overlay.querySelector('#visual-editor-wrap');
    const sourceEditorWrap = overlay.querySelector('#source-editor-wrap');
    const editorIframe = overlay.querySelector('#visual-editor');
    const sourceTextarea = overlay.querySelector('#source-editor');

    function updateTemplateLabels() {
        overlay.querySelectorAll('#template-selector label').forEach(lbl => {
            const radio = lbl.querySelector('input[type=radio]');
            if (radio.checked) {
                lbl.style.borderColor = radio.value === 'umit' ? 'var(--primary)' : (radio.value === 'custom' ? 'var(--warning)' : '#d72710');
                lbl.style.background = radio.value === 'umit' ? 'rgba(107,99,255,0.08)' : (radio.value === 'custom' ? 'rgba(245,158,11,0.08)' : 'rgba(215,39,16,0.08)');
            } else {
                lbl.style.borderColor = 'var(--border)';
                lbl.style.background = 'transparent';
            }
        });
    }

    function loadVisualEditor(html) {
        const doc = editorIframe.contentDocument || editorIframe.contentWindow.document;
        // Inject <base href> so relative paths (/campaign-assets/...) resolve correctly
        const baseTag = `<base href="${window.location.origin}/">`;
        const htmlWithBase = html.replace(/(<head[^>]*>)/i, `$1${baseTag}`);
        doc.open();
        doc.write(htmlWithBase.includes('<head') ? htmlWithBase : baseTag + html);
        doc.close();
        // Make content editable
        setTimeout(() => {
            doc.body.setAttribute('contenteditable', 'true');
            doc.body.style.cursor = 'text';
            // Add editing styles
            const style = doc.createElement('style');
            style.textContent = `
                [contenteditable]:focus { outline: 2px dashed #d72710; outline-offset: 2px; }
                td:hover, p:hover, a:hover, span:hover { outline: 1px dashed rgba(215,39,16,0.3); cursor: text; }
            `;
            doc.head.appendChild(style);
        }, 100);
    }

    function getVisualHtml() {
        const doc = editorIframe.contentDocument || editorIframe.contentWindow.document;
        if (!doc || !doc.documentElement) return '';
        // Remove editing artifacts
        doc.body.removeAttribute('contenteditable');
        const edited = '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
        doc.body.setAttribute('contenteditable', 'true');
        return edited;
    }

    async function switchTemplate(slug) {
        currentTemplate = slug;
        updateTemplateLabels();

        if (slug === 'umit') {
            umitArea.style.display = '';
            htmlEditorArea.style.display = 'none';
        } else {
            umitArea.style.display = 'none';
            htmlEditorArea.style.display = '';

            if (slug === 'custom') {
                // Custom HTML — empty editor
                sourceTextarea.value = '';
                loadVisualEditor('<html><body><p>Введите ваш HTML здесь</p></body></html>');
            } else {
                // Load Prom28 template
                if (templateHtmlCache[slug]) {
                    sourceTextarea.value = templateHtmlCache[slug];
                    loadVisualEditor(templateHtmlCache[slug]);
                } else {
                    try {
                        const result = await api.get(`/api/campaign-templates/${slug}`);
                        templateHtmlCache[slug] = result.html;
                        sourceTextarea.value = result.html;
                        loadVisualEditor(result.html);
                    } catch (e) {
                        showToast('Ошибка загрузки шаблона: ' + e.message, 'error');
                    }
                }
            }

            // Reset to visual mode
            isSourceMode = false;
            visualEditorWrap.style.display = '';
            sourceEditorWrap.style.display = 'none';
            overlay.querySelector('#btn-visual-mode').disabled = true;
            overlay.querySelector('#btn-source-mode').disabled = false;
        }
    }

    overlay.querySelectorAll('input[name="camp-template"]').forEach(radio => {
        radio.addEventListener('change', () => switchTemplate(radio.value));
    });

    // Visual / Source mode toggle
    overlay.querySelector('#btn-visual-mode').addEventListener('click', () => {
        // Switching from source to visual
        isSourceMode = false;
        const html = sourceTextarea.value;
        loadVisualEditor(html);
        visualEditorWrap.style.display = '';
        sourceEditorWrap.style.display = 'none';
        overlay.querySelector('#btn-visual-mode').disabled = true;
        overlay.querySelector('#btn-source-mode').disabled = false;
    });

    overlay.querySelector('#btn-source-mode').addEventListener('click', () => {
        // Switching from visual to source
        isSourceMode = true;
        sourceTextarea.value = getVisualHtml();
        visualEditorWrap.style.display = 'none';
        sourceEditorWrap.style.display = '';
        overlay.querySelector('#btn-source-mode').disabled = true;
        overlay.querySelector('#btn-visual-mode').disabled = false;
    });

    // Save handler
    overlay.querySelector('#save-campaign').addEventListener('click', async () => {
        const name = overlay.querySelector('#camp-name').value.trim();
        const subject = overlay.querySelector('#camp-subject').value.trim();
        const recipients = overlay.querySelector('#camp-recipients').value;
        const delay_seconds = parseInt(delaySlider.value);

        if (!name) { showToast('Укажите название', 'error'); return; }
        if (!subject) { showToast('Укажите тему письма', 'error'); return; }

        let html_body = '';
        if (currentTemplate === 'umit') {
            html_body = overlay.querySelector('#camp-body').value.trim();
            // Auto-convert plain text line breaks to <br> if no HTML tags present
            if (html_body && !html_body.includes('<')) {
                html_body = html_body.replace(/\n/g, '<br>');
            }
        } else {
            // Get HTML from editor
            html_body = isSourceMode ? sourceTextarea.value : getVisualHtml();
        }

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
                        <button class="btn btn-secondary btn-sm" id="btn-preview">
                            <span class="material-symbols-outlined" style="font-size:14px">visibility</span> Предпросмотр
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

        <!-- Email Preview -->
        <div class="card mb-16" id="preview-container" style="display:none">
            <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
                <h3>Предпросмотр письма</h3>
                <button class="btn btn-sm btn-secondary" id="btn-close-preview">
                    <span class="material-symbols-outlined" style="font-size:14px">close</span> Закрыть
                </button>
            </div>
            <div style="padding:10px;background:#f8f8f8;border-radius:0 0 8px 8px">
                <iframe id="preview-iframe" style="width:100%;height:600px;border:1px solid var(--border);border-radius:6px;background:#fff" sandbox="allow-same-origin"></iframe>
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

        <!-- Confirmation Modal (hidden) -->
        <div id="confirm-modal-overlay" class="modal-overlay" style="display:none">
            <div class="modal" style="max-width:400px">
                <div class="modal-header">
                    <h3>Подтверждение запуска</h3>
                </div>
                <div class="modal-body" style="text-align:center;padding:20px">
                    <span class="material-symbols-outlined" style="font-size:48px;color:var(--primary);margin-bottom:10px">rocket_launch</span>
                    <p style="margin:10px 0;font-size:14px">Запустить рассылку <strong>«${data.name}»</strong>?</p>
                    <p style="margin:0;font-size:12px;color:var(--text-muted)">Будет отправлено <strong>${data.total_recipients}</strong> писем</p>
                </div>
                <div class="modal-footer" style="justify-content:center;gap:12px">
                    <button class="btn btn-secondary" id="confirm-cancel">Отмена</button>
                    <button class="btn btn-primary" id="confirm-send">
                        <span class="material-symbols-outlined" style="font-size:14px">send</span> Запустить
                    </button>
                </div>
            </div>
        </div>
    `;

    // Event handlers
    const btnSend = container.querySelector('#btn-send');
    if (btnSend) {
        btnSend.addEventListener('click', () => {
            const modal = container.querySelector('#confirm-modal-overlay');
            modal.style.display = 'flex';
        });

        container.querySelector('#confirm-cancel').addEventListener('click', () => {
            container.querySelector('#confirm-modal-overlay').style.display = 'none';
        });

        container.querySelector('#confirm-send').addEventListener('click', async () => {
            container.querySelector('#confirm-modal-overlay').style.display = 'none';
            btnSend.disabled = true;
            btnSend.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px">hourglass_top</span> Запуск...';
            try {
                await api.post(`/api/campaigns/${campaignId}/send`);
                showToast('Рассылка запущена!', 'success');
                renderCampaignDetail(container, campaignId);
            } catch (e) {
                showToast('Ошибка запуска: ' + e.message, 'error');
                btnSend.disabled = false;
                btnSend.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px">send</span> Запустить';
            }
        });
    }

    // Preview button
    const btnPreview = container.querySelector('#btn-preview');
    if (btnPreview) {
        btnPreview.addEventListener('click', async () => {
            const previewContainer = container.querySelector('#preview-container');
            const iframe = container.querySelector('#preview-iframe');
            previewContainer.style.display = 'block';
            try {
                const resp = await fetch(`/api/campaigns/${campaignId}/preview`, { method: 'POST' });
                const html = await resp.text();
                iframe.srcdoc = html;
            } catch (e) {
                iframe.srcdoc = '<p style="padding:20px;color:red">Ошибка загрузки предпросмотра</p>';
            }
            previewContainer.scrollIntoView({ behavior: 'smooth' });
        });

        container.querySelector('#btn-close-preview').addEventListener('click', () => {
            container.querySelector('#preview-container').style.display = 'none';
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
                            ${(() => {
                                // Section mapping from 123.txt — maps test codes to logical sections
                                const SECTION_MAP = {
                                    // === Общедоступная часть ===
                                    'T01':'Общедоступная часть','T02':'Общедоступная часть','T03':'Общедоступная часть','T04':'Общедоступная часть',
                                    'B01':'Общедоступная часть','B02':'Общедоступная часть','B03':'Общедоступная часть','B04':'Общедоступная часть','B05':'Общедоступная часть',
                                    // === Расширенный поиск ===
                                    'T05':'Расширенный поиск',
                                    'B06':'Расширенный поиск','B07':'Расширенный поиск','B08':'Расширенный поиск','B09':'Расширенный поиск','B10':'Расширенный поиск','B11':'Расширенный поиск',
                                    // === Поле поиска ===
                                    'B12':'Поле поиска','B13':'Поле поиска',
                                    // === Новые заявки ===
                                    'T06':'Новые заявки','T07':'Новые заявки',
                                    'B14':'Новые заявки','B15':'Новые заявки','B16':'Новые заявки','B17':'Новые заявки','B18':'Новые заявки','B19':'Новые заявки',
                                    // === Детальная карточки заявки ===
                                    'T08':'Детальная карточки заявки',
                                    'B20':'Детальная карточки заявки','B21':'Детальная карточки заявки','B22':'Детальная карточки заявки','B23':'Детальная карточки заявки','B24':'Детальная карточки заявки','B25':'Детальная карточки заявки',
                                    // === Новые товары ===
                                    'T09':'Новые товары',
                                    'B26':'Новые товары','B27':'Новые товары','B28':'Новые товары','B29':'Новые товары','B30':'Новые товары',
                                    // === Детальная карточка товара ===
                                    'B31':'Детальная карточка товара','B32':'Детальная карточка товара','B33':'Детальная карточка товара','B34':'Детальная карточка товара','B35':'Детальная карточка товара',
                                    // === Все заявки ===
                                    'B36':'Все заявки','B37':'Все заявки','B38':'Все заявки','B39':'Все заявки','B40':'Все заявки','B41':'Все заявки','B42':'Все заявки',
                                    // === Все товары ===
                                    'B43':'Все товары','B44':'Все товары','B45':'Все товары','B46':'Все товары','B47':'Все товары','B48':'Все товары',
                                    // === Футер ===
                                    'T10':'Футер','T11':'Футер','T12':'Футер','T13':'Футер','T14':'Футер','T15':'Футер','T16':'Футер','T17':'Футер',
                                    'B49':'Футер','B50':'Футер','B51':'Футер','B52':'Футер',
                                    // === Авторизация ===
                                    'B53':'Авторизация','B54':'Авторизация','B55':'Авторизация','B56':'Авторизация','B57':'Авторизация','B58':'Авторизация','B59':'Авторизация',
                                    // === Форма восстановления пароля ===
                                    'B60':'Восстановление пароля','B61':'Восстановление пароля','B62':'Восстановление пароля',
                                    // === Форма регистрации ===
                                    'B63':'Регистрация','B64':'Регистрация','B65':'Регистрация','B66':'Регистрация','B67':'Регистрация','B68':'Регистрация',
                                    // === Профиль покупателя — Заявки ===
                                    'T18':'API Заявки','T19':'API Заявки','T20':'API Заявки','T21':'SSL/Время ответа','T22':'SSL/Время ответа','T23':'SSL/Время ответа',
                                    'T24':'Авторизация покупателя','T25':'Заявки (API)','T26':'Заявки (API)','T27':'Заявки (API)','T28':'Заявки (API)','T29':'Заявки (API)',
                                    'T30':'Избранное (API)','T31':'Избранное (API)','T32':'История заявок (API)','T33':'Заявки (API)','T34':'Заявки (API)','T35':'Заявки (API)',
                                    // === Создание заявки ===
                                    'B69':'Создание заявки','B70':'Создание заявки','B71':'Создание заявки','B72':'Создание заявки','B73':'Создание заявки',
                                    'B74':'Создание заявки','B75':'Создание заявки','B76':'Создание заявки','B77_UI':'Создание заявки','B78_UI':'Создание заявки',
                                    'B79_UI':'Создание заявки','B80_UI':'Создание заявки','B81_UI':'Создание заявки','B82':'Создание заявки',
                                    // === Перемещение в историю ===
                                    'B83':'Перемещение в историю','B84':'Перемещение в историю','B85':'Перемещение в историю','B86':'Перемещение в историю','B87':'Перемещение в историю',
                                    // === Форма создания заявки ===
                                    'B88':'Форма создания заявки','B89':'Форма создания заявки','B90':'Форма создания заявки','B91':'Форма создания заявки',
                                    'B92':'Форма создания заявки','B93':'Форма создания заявки',
                                    // === Страница Заявки ===
                                    'B94':'Страница Заявки','B95':'Страница Заявки','B96':'Страница Заявки','B97':'Страница Заявки','B98':'Страница Заявки',
                                    // === Ссылки (авторизован) ===
                                    'T36':'Ссылки (авторизован)','T37':'Ссылки (авторизован)','T38':'Ссылки (авторизован)','T39':'Ссылки (авторизован)',
                                    'T40':'Ссылки (авторизован)','T41':'Ссылки (авторизован)','T42':'Ссылки (авторизован)',
                                    // === Склад ===
                                    'T43':'Склад (API)','T44':'Склад (API)','T45':'Склад (API)','T46':'Склад (API)',
                                    'B99':'Склад','B100':'Склад','B101':'Склад','B102':'Склад','B103':'Склад','B104':'Склад','B105':'Склад',
                                    'B106':'Склад — подборки','B107':'Склад — подборки','B108':'Склад — подборки',
                                    // === Корзина ===
                                    'T47':'Корзина (API)','T48':'Корзина (API)','T49':'Корзина (API)','T50':'Корзина (API)','T51':'Корзина (API)','T52':'Корзина (API)',
                                    'B109':'Корзина','B110':'Корзина','B111':'Корзина','B112':'Корзина',
                                    // === Продавец / Витрина ===
                                    'T53':'Продавец / Витрина (API)','T54':'Продавец / Витрина (API)','T55':'Продавец / Витрина (API)',
                                    // === Заказы ===
                                    'T56':'Заказы (API)','T57':'Заказы (API)','T58':'Заказы (API)','T59':'Заказы (API)',
                                    'B113':'Заказы','B114':'Заказы','B115':'Заказы','B116':'Заказы',
                                    // === Аккаунт ===
                                    'T60':'Аккаунт (API)',
                                    'B117':'Аккаунт','B118':'Аккаунт','B119':'Аккаунт',
                                    // === Профиль ===
                                    'T61':'Профиль (API)','T62':'Профиль (API)',
                                    'B120':'Профиль',
                                    // === Техника ===
                                    'T63':'Техника (API)','T64':'Техника (API)','T65':'Техника (API)','T66':'Техника (API)',
                                    'T67':'Техника (API)','T68':'Техника (API)','T69':'Техника (API)','T70':'Техника (API)',
                                    'B121':'Техника','B122':'Техника','B123':'Техника','B124':'Техника',
                                    // === Рейтинг / Партнёрская / Документы ===
                                    'T71':'Рейтинг / Документы (API)','T72':'Рейтинг / Документы (API)','T73':'Рейтинг / Документы (API)',
                                    'T74':'Рейтинг / Документы (API)','T75':'Рейтинг / Документы (API)','T76':'Рейтинг / Документы (API)',
                                    'B125':'Рейтинг / Документы','B126':'Рейтинг / Документы','B127':'Рейтинг / Документы',
                                    // === Продавец (UI) ===
                                    'T77':'Продавец','T78':'Продавец','T79':'Продавец','T80':'Продавец','T81':'Продавец',
                                    'B128':'Продавец','B129':'Продавец','B130':'Продавец',
                                    // === Сообщения ===
                                    'B131':'Сообщения','B132':'Сообщения','B133':'Сообщения','B134':'Сообщения',
                                    'B135':'Сообщения','B136':'Сообщения','B137':'Сообщения','B138':'Сообщения',
                                };
                                const SECTION_ICONS = {
                                    'Общедоступная часть':'public','Расширенный поиск':'search','Поле поиска':'manage_search',
                                    'Новые заявки':'assignment','Детальная карточки заявки':'description','Новые товары':'inventory_2',
                                    'Детальная карточка товара':'info','Все заявки':'list_alt','Все товары':'view_list',
                                    'Футер':'dock_to_bottom','Авторизация':'lock','Восстановление пароля':'lock_reset',
                                    'Регистрация':'person_add','Создание заявки':'add_circle','Перемещение в историю':'history',
                                    'Форма создания заявки':'edit_note','Страница Заявки':'assignment','Склад':'warehouse',
                                    'Склад — подборки':'collections_bookmark','Корзина':'shopping_cart','Заказы':'receipt_long',
                                    'Аккаунт':'account_circle','Профиль':'badge','Техника':'directions_car',
                                    'Рейтинг / Документы':'star','Продавец':'storefront','Сообщения':'chat',
                                };
                                // Build sections in order
                                const sectionOrder = [];
                                const sections = {};
                                testsData.tests.forEach(t => {
                                    const sec = SECTION_MAP[t.code] || t.group;
                                    if (!sections[sec]) { sections[sec] = []; sectionOrder.push(sec); }
                                    sections[sec].push(t);
                                });
                                let html = '';
                                sectionOrder.forEach(sec => {
                                    const tests = sections[sec];
                                    if (!tests || tests.length === 0) return;
                                    const passCount = tests.filter(t => t.last_status === 'pass').length;
                                    const failCount = tests.filter(t => ['fail','error'].includes(t.last_status)).length;
                                    const skipCount = tests.filter(t => ['skip','unknown'].includes(t.last_status)).length;
                                    const icon = SECTION_ICONS[sec] || 'folder';
                                    const secId = sec.replace(/[^a-zA-Zа-яА-Я0-9]/g,'_');
                                    html += '<tr class="mon-group-header" data-group="'+secId+'" style="cursor:pointer;background:linear-gradient(90deg,var(--primary)08,transparent)">';
                                    html += '<td colspan="8" style="padding:8px 16px;font-weight:700;font-size:13px;border-bottom:2px solid var(--primary);border-left:3px solid var(--primary)">';
                                    html += '<span style="display:flex;align-items:center;gap:8px">';
                                    html += '<span class="material-symbols-outlined" style="font-size:18px;color:var(--primary)">'+icon+'</span>';
                                    html += sec;
                                    html += ' <span style="font-weight:400;font-size:11px;color:var(--text-muted)">('+tests.length+')</span>';
                                    html += '<span style="margin-left:auto;display:flex;gap:8px;font-size:12px">';
                                    if (passCount > 0) html += '<span style="color:var(--success)">✓ '+passCount+'</span>';
                                    if (failCount > 0) html += '<span style="color:var(--danger)">✗ '+failCount+'</span>';
                                    if (skipCount > 0) html += '<span style="color:var(--text-muted)">⊘ '+skipCount+'</span>';
                                    html += '</span></span></td></tr>';
                                    tests.forEach(t => {
                                        html += '<tr data-status="'+t.last_status+'" data-group="'+secId+'">';
                                        html += '<td><code style="font-size:11px;color:var(--primary)">'+t.code+'</code></td>';
                                        html += '<td style="font-size:13px">'+t.name+'</td>';
                                        html += '<td><span style="font-size:10px;padding:2px 6px;border-radius:3px;background:var(--bg-hover);color:var(--text-muted)">'+t.group+'</span></td>';
                                        html += '<td>'+monitorBadge(t.last_status)+'</td>';
                                        html += '<td style="font-size:12px;color:var(--text-muted)">'+t.last_duration_ms+'ms</td>';
                                        html += '<td style="font-size:12px">'+(t.last_response_code||'—')+'</td>';
                                        html += '<td style="font-size:12px;color:var(--danger);max-width:400px;white-space:normal;word-break:break-word;line-height:1.4" title="'+(t.last_error||'').replace(/"/g,'&quot;')+'">'+(t.last_error||'')+'</td>';
                                        html += '<td><button class="btn btn-sm btn-ghost mon-rerun" data-id="'+t.id+'" title="Запустить"><span class="material-symbols-outlined" style="font-size:16px">replay</span></button></td>';
                                        html += '</tr>';
                                    });
                                });
                                return html;
                            })()}
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
                if (r.classList.contains('mon-group-header')) { r.style.display = ''; return; }
                r.style.display = r.dataset.status === 'pass' ? '' : 'none';
            });
        });
        document.getElementById('mon-filter-fail')?.addEventListener('click', () => {
            document.querySelectorAll('#mon-tests-table tbody tr').forEach(r => {
                if (r.classList.contains('mon-group-header')) { r.style.display = ''; return; }
                r.style.display = ['fail','error'].includes(r.dataset.status) ? '' : 'none';
            });
        });

        // Event: Collapse/expand groups
        document.querySelectorAll('.mon-group-header').forEach(header => {
            header.addEventListener('click', () => {
                const group = header.dataset.group;
                const rows = document.querySelectorAll('#mon-tests-table tbody tr[data-group="'+group+'"]:not(.mon-group-header)');
                const firstRow = rows[0];
                const isHidden = firstRow && firstRow.style.display === 'none';
                rows.forEach(r => r.style.display = isHidden ? '' : 'none');
                header.style.opacity = isHidden ? '1' : '0.7';
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

// ═══════════════════════════════════════════════════
//  PAGE: Reports (Click Tracking)
// ═══════════════════════════════════════════════════
let reportsPage = 1;
async function renderReports(container) {
    try {
        const data = await api.get(`/api/dashboard/clicks?page=${reportsPage}&page_size=25`);

        const formatTimeDelta = (seconds) => {
            if (!seconds && seconds !== 0) return '—';
            if (seconds < 60) return `${seconds}с`;
            if (seconds < 3600) return `${Math.floor(seconds/60)}мин ${seconds%60}с`;
            const h = Math.floor(seconds/3600);
            const m = Math.floor((seconds%3600)/60);
            return `${h}ч ${m}мин`;
        };

        container.innerHTML = `
            <!-- KPI Cards -->
            <div class="kpi-grid" style="margin-bottom:24px">
                <div class="kpi-card">
                    <span class="material-symbols-outlined kpi-icon" style="color:var(--primary)">ads_click</span>
                    <div class="kpi-value">${data.total_clicks}</div>
                    <div class="kpi-label">Всего кликов</div>
                </div>
                <div class="kpi-card">
                    <span class="material-symbols-outlined kpi-icon" style="color:var(--success)">people</span>
                    <div class="kpi-value">${data.unique_clickers}</div>
                    <div class="kpi-label">Уникальных поставщиков</div>
                </div>
                <div class="kpi-card">
                    <span class="material-symbols-outlined kpi-icon" style="color:var(--warning)">send</span>
                    <div class="kpi-value">${data.total_sent}</div>
                    <div class="kpi-label">Отправлено писем</div>
                </div>
                <div class="kpi-card">
                    <span class="material-symbols-outlined kpi-icon" style="color:${data.click_rate > 5 ? 'var(--success)' : 'var(--danger)'}">trending_up</span>
                    <div class="kpi-value">${data.click_rate}%</div>
                    <div class="kpi-label">Click Rate</div>
                </div>
            </div>

            <!-- Clicks Table -->
            <div class="card">
                <div class="section-header">
                    <span class="material-symbols-outlined">touch_app</span>
                    <h3>Детализация переходов</h3>
                    <span style="margin-left:auto;font-size:13px;color:var(--text-muted)">За последние 30 дней</span>
                </div>
                <div class="card-body" style="padding:0">
                    ${data.items.length === 0 ? `
                        <div class="empty-state" style="padding:40px">
                            <span class="material-symbols-outlined">mouse</span>
                            <p>Пока нет переходов по ссылкам</p>
                        </div>
                    ` : `
                        <div class="table-wrapper">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Поставщик</th>
                                        <th>Email</th>
                                        <th>Заявка</th>
                                        <th>Время клика</th>
                                        <th>Время отклика</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.items.map(item => `
                                        <tr>
                                            <td><strong>${item.supplier_name}</strong></td>
                                            <td style="font-size:12px;color:var(--text-muted)">${item.supplier_email}</td>
                                            <td>
                                                <a href="#/bids/${item.bid_id}/logs" style="color:var(--primary);text-decoration:none">
                                                    №${item.bid_source_id}
                                                </a>
                                                <span style="font-size:12px;display:block;color:var(--text-muted)">${item.bid_name.substring(0, 40)}${item.bid_name.length > 40 ? '…' : ''}</span>
                                            </td>
                                            <td style="font-size:13px">${item.clicked_at ? new Date(item.clicked_at).toLocaleString('ru') : '—'}</td>
                                            <td>
                                                <span class="badge ${item.time_to_click_seconds < 3600 ? 'badge-success' : item.time_to_click_seconds < 86400 ? 'badge-warning' : 'badge-default'}" style="font-size:12px">
                                                    ${formatTimeDelta(item.time_to_click_seconds)}
                                                </span>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        <div style="display:flex;justify-content:center;gap:8px;padding:16px">
                            <button class="btn btn-secondary" id="reports-prev" ${reportsPage <= 1 ? 'disabled' : ''}>← Назад</button>
                            <span style="padding:8px 16px;color:var(--text-muted);font-size:13px">Страница ${data.page}</span>
                            <button class="btn btn-secondary" id="reports-next" ${data.items.length < 25 ? 'disabled' : ''}>Вперёд →</button>
                        </div>
                    `}
                </div>
            </div>
        `;

        // Pagination
        document.getElementById('reports-prev')?.addEventListener('click', () => {
            reportsPage = Math.max(1, reportsPage - 1);
            renderReports(container);
        });
        document.getElementById('reports-next')?.addEventListener('click', () => {
            reportsPage++;
            renderReports(container);
        });

    } catch (e) {
        container.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
    }
}

// ═══════════════════════════════════════════════════
//  PAGE: Promotion (Yandex Direct)
// ═══════════════════════════════════════════════════
async function renderPromotion(container) {
    const [config, campaignsData] = await Promise.all([
        api.get('/api/promotion/config'),
        api.get('/api/promotion/campaigns').catch(() => ({ campaigns: [], totals: {} })),
    ]);

    const t = campaignsData.totals || {};
    const campaigns = campaignsData.campaigns || [];
    const hasToken = config.has_token;
    const connected = config.connected;
    const hasCampaigns = campaigns.length > 0;

    // State 1: Not connected — show connect form
    if (!hasToken) {
        container.innerHTML = `
            <div style="max-width:600px;margin:40px auto;text-align:center">
                <div style="width:80px;height:80px;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:20px;display:flex;align-items:center;justify-content:center;margin:0 auto 24px">
                    <span class="material-symbols-outlined" style="font-size:40px;color:#fff">trending_up</span>
                </div>
                <h2 style="font-size:28px;font-weight:800;margin:0 0 8px">Продвижение в Яндекс.Директ</h2>
                <p style="color:var(--text-secondary);font-size:15px;margin:0 0 32px;line-height:1.6">
                    Запустите рекламу ваших услуг в поиске Яндекса.
                    Подключите аккаунт Яндекс.Директ и управляйте кампаниями прямо из панели.
                </p>

                <div class="card" style="text-align:left;padding:24px">
                    <h3 style="margin:0 0 16px;font-size:16px">Подключение аккаунта</h3>
                    <div class="form-group">
                        <label class="form-label">OAuth-токен *</label>
                        <p class="form-hint">Получите на <a href="https://oauth.yandex.ru/" target="_blank" style="color:var(--primary)">oauth.yandex.ru</a></p>
                        <input class="form-input" id="yd-token" type="password" placeholder="y0_AgAAAA...">
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">Client ID</label>
                            <input class="form-input" id="yd-client-id" placeholder="ID приложения">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Логин</label>
                            <input class="form-input" id="yd-login" placeholder="login (необязательно)">
                        </div>
                    </div>
                    <button class="btn btn-primary" id="btn-yd-connect" style="width:100%;margin-top:8px">
                        <span class="material-symbols-outlined">link</span> Подключить Яндекс.Директ
                    </button>
                </div>

                <div style="margin-top:24px;padding:16px;background:var(--bg-input);border-radius:12px;text-align:left">
                    <p style="margin:0;font-size:13px;color:var(--text-muted)">
                        <span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle;margin-right:4px">info</span>
                        Для получения токена: зарегистрируйте приложение на <a href="https://oauth.yandex.ru/client/new" target="_blank" style="color:var(--primary)">oauth.yandex.ru/client/new</a>,
                        выберите права «Яндекс.Директ», получите токен через OAuth-авторизацию.
                    </p>
                </div>
            </div>
        `;

        document.getElementById('btn-yd-connect')?.addEventListener('click', async () => {
            const token = document.getElementById('yd-token').value.trim();
            if (!token) return showToast('Укажите OAuth-токен', 'error');

            const btn = document.getElementById('btn-yd-connect');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;margin:0;border-width:2px"></div> Проверка...';

            try {
                const result = await api.post('/api/promotion/config', {
                    oauth_token: token,
                    client_id: document.getElementById('yd-client-id').value.trim(),
                    client_login: document.getElementById('yd-login').value.trim(),
                });
                showToast(result.message, result.connected ? 'success' : 'error');
                if (result.connected) setTimeout(() => renderPromotion(container), 500);
                else { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined">link</span> Подключить'; }
            } catch (e) {
                showToast('Ошибка: ' + e.message, 'error');
                btn.disabled = false;
                btn.innerHTML = '<span class="material-symbols-outlined">link</span> Подключить';
            }
        });
        return;
    }

    // State 2+3: Connected — tabbed interface
    let activePromTab = window._promTab || 'campaigns';

    container.innerHTML = `
        <div class="action-bar" style="margin-bottom:0">
            <div style="display:flex;align-items:center;gap:12px">
                <div style="width:10px;height:10px;border-radius:50%;background:${connected ? 'var(--success)' : 'var(--danger)'}"></div>
                <span style="font-size:14px;font-weight:600;color:${connected ? 'var(--success)' : 'var(--danger)'}">
                    ${connected ? 'Подключён к Яндекс.Директ' : 'Нет подключения'}
                </span>
                ${config.client_login ? `<span style="font-size:12px;color:var(--text-muted)">(${config.client_login})</span>` : ''}
            </div>
            <button class="btn btn-sm" style="color:var(--text-muted);font-size:12px" id="btn-yd-disconnect">
                <span class="material-symbols-outlined" style="font-size:14px">link_off</span> Отключить
            </button>
        </div>

        <!-- Tabs -->
        <div style="display:flex;gap:0;border-bottom:2px solid var(--border);margin:16px 0 24px">
            <button class="prom-tab ${activePromTab==='campaigns'?'active':''}" data-tab="campaigns">
                <span class="material-symbols-outlined" style="font-size:18px">campaign</span> Кампании
            </button>
            <button class="prom-tab ${activePromTab==='catalog'?'active':''}" data-tab="catalog">
                <span class="material-symbols-outlined" style="font-size:18px">directions_car</span> Справочник
            </button>
            <button class="prom-tab ${activePromTab==='keywords'?'active':''}" data-tab="keywords">
                <span class="material-symbols-outlined" style="font-size:18px">key</span> Ключевики
            </button>
        </div>

        <div id="prom-tab-content"></div>

        ${config.last_sync ? `<p style="text-align:right;font-size:12px;color:var(--text-muted);margin-top:12px">Последняя синхронизация: ${new Date(config.last_sync).toLocaleString('ru-RU')}</p>` : ''}
    `;

    // Tab styles (inject once)
    if (!document.getElementById('prom-tab-styles')) {
        const style = document.createElement('style');
        style.id = 'prom-tab-styles';
        style.textContent = `
            .prom-tab { background:none;border:none;padding:10px 20px;font-size:14px;font-weight:500;color:var(--text-muted);cursor:pointer;display:flex;align-items:center;gap:6px;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all 0.2s }
            .prom-tab:hover { color:var(--text-primary);background:var(--bg-input);border-radius:8px 8px 0 0 }
            .prom-tab.active { color:var(--primary);border-bottom-color:var(--primary);font-weight:600 }
            .brand-chip { display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:500;background:var(--bg-input);border:1px solid var(--border);cursor:pointer;transition:all 0.15s }
            .brand-chip:hover { border-color:var(--primary);color:var(--primary) }
            .brand-chip.selected { background:var(--primary);color:#fff;border-color:var(--primary) }
            .cluster-badge { display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase }
        `;
        document.head.appendChild(style);
    }

    const clusterColors = {
        'тормоза':'#ef4444','подвеска':'#3b82f6','привод':'#8b5cf6','двигатель':'#f59e0b',
        'фильтры':'#10b981','электрика':'#6366f1','кузов':'#ec4899','выхлоп':'#64748b'
    };

    // ── Tab: Campaigns ──
    async function renderCampaignsTab(tabEl) {
        const statusColors = { active: 'var(--success)', paused: 'var(--warning)', pending: 'var(--primary)', stopped: 'var(--danger)', draft: 'var(--text-muted)', archived: 'var(--text-muted)' };
        const statusLabels = { active: 'Активна', paused: 'На паузе', pending: 'Модерация', stopped: 'Остановлена', draft: 'Черновик', archived: 'Архив' };

        tabEl.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);gap:12px;flex:1;margin-right:16px">
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Показы</div><div class="kpi-value" style="font-size:20px">${(t.impressions||0).toLocaleString()}</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Клики</div><div class="kpi-value" style="font-size:20px">${(t.clicks||0).toLocaleString()}</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">CTR</div><div class="kpi-value" style="font-size:20px">${t.ctr||0}%</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Расход</div><div class="kpi-value" style="font-size:20px">${(t.cost||0).toLocaleString()} ₽</div></div>
                </div>
                <div style="display:flex;gap:8px;flex-shrink:0">
                    <button class="btn btn-secondary" id="btn-yd-sync"><span class="material-symbols-outlined">sync</span> Синхронизировать</button>
                    <button class="btn btn-primary" id="btn-yd-enable"><span class="material-symbols-outlined">add_circle</span> Новая</button>
                </div>
            </div>

            ${!hasCampaigns ? `
            <div class="card" style="text-align:center;padding:48px">
                <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">campaign</span>
                <p style="color:var(--text-secondary);margin:12px 0 0">Нет кампаний. Перейдите во вкладку «Ключевики» для пакетного создания.</p>
            </div>` : `
            <div class="card">
                <table class="data-table">
                    <thead><tr><th>Кампания</th><th>Статус</th><th>Показы</th><th>Клики</th><th>CTR</th><th>Расход</th><th>Бюджет/день</th><th>Действия</th></tr></thead>
                    <tbody>
                        ${campaigns.map(c => `<tr>
                            <td style="font-weight:600">${c.name}</td>
                            <td><span style="color:${statusColors[c.status]||'var(--text-muted)'};font-weight:600;font-size:13px">${statusLabels[c.status]||c.status}</span></td>
                            <td>${c.impressions.toLocaleString()}</td>
                            <td style="font-weight:600;color:var(--primary)">${c.clicks.toLocaleString()}</td>
                            <td>${c.ctr}%</td>
                            <td>${c.cost.toLocaleString()} ₽</td>
                            <td style="color:var(--text-secondary)">${c.daily_budget} ₽</td>
                            <td>
                                ${c.status==='active'?`<button class="btn btn-sm btn-secondary" onclick="ydPauseCampaign(${c.id})"><span class="material-symbols-outlined">pause</span></button>`:
                                  c.status==='paused'?`<button class="btn btn-sm btn-primary" onclick="ydResumeCampaign(${c.id})"><span class="material-symbols-outlined">play_arrow</span></button>`:
                                  `<span style="color:var(--text-muted);font-size:12px">${c.yd_status||'—'}</span>`}
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>`}
        `;

        document.getElementById('btn-yd-sync')?.addEventListener('click', async () => {
            const btn = document.getElementById('btn-yd-sync');
            btn.disabled = true; btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;margin:0;border-width:2px"></div> Синхронизация...';
            try { const r = await api.post('/api/promotion/sync', {}); showToast(r.message, 'success'); setTimeout(() => renderPromotion(container), 500); }
            catch (e) { showToast('Ошибка: ' + e.message, 'error'); btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined">sync</span> Синхронизировать'; }
        });
        document.getElementById('btn-yd-enable')?.addEventListener('click', () => showEnableCampaignModal(container));
    }

    // ── Tab: Catalog ──
    async function renderCatalogTab(tabEl) {
        tabEl.innerHTML = '<div class="spinner"></div>';
        try {
            const [brandsData, partsData] = await Promise.all([
                api.get('/api/promotion/brands'),
                api.get('/api/promotion/parts'),
            ]);
            const brands = brandsData.brands || [];
            const clusters = partsData.clusters || {};

            tabEl.innerHTML = `
                <div style="display:flex;gap:24px">
                    <!-- Brands -->
                    <div style="flex:2">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                            <h3 style="margin:0;font-size:16px">Марки и модели (${brands.length})</h3>
                            <div style="display:flex;gap:8px">
                                <button class="btn btn-sm btn-secondary" id="btn-seed-catalog">
                                    <span class="material-symbols-outlined" style="font-size:16px">database</span> Seed
                                </button>
                                <button class="btn btn-sm btn-primary" id="btn-add-brand">
                                    <span class="material-symbols-outlined" style="font-size:16px">add</span> Марка
                                </button>
                            </div>
                        </div>
                        ${brands.length === 0 ? `
                        <div class="card" style="text-align:center;padding:40px">
                            <span class="material-symbols-outlined" style="font-size:40px;color:var(--text-muted)">directions_car</span>
                            <p style="color:var(--text-secondary);margin:12px 0">Справочник пуст. Нажмите «Seed» для загрузки 33 марок.</p>
                        </div>` : `
                        <div class="card" style="max-height:500px;overflow-y:auto">
                            <table class="data-table">
                                <thead><tr><th>Марка</th><th>RU</th><th>Моделей</th><th></th></tr></thead>
                                <tbody>
                                    ${brands.map(b => `<tr style="cursor:pointer" class="brand-row" data-brand-id="${b.id}">
                                        <td style="font-weight:600">${b.name}</td>
                                        <td style="color:var(--text-secondary);font-size:13px">${b.name_ru||'—'}</td>
                                        <td><span class="badge pending">${b.model_count}</span></td>
                                        <td style="width:40px"><button class="btn btn-sm btn-danger" onclick="event.stopPropagation();deleteBrand(${b.id})"><span class="material-symbols-outlined" style="font-size:16px">delete</span></button></td>
                                    </tr>`).join('')}
                                </tbody>
                            </table>
                        </div>`}

                        <!-- Models detail panel -->
                        <div id="brand-models-panel" style="margin-top:16px"></div>
                    </div>

                    <!-- Part categories -->
                    <div style="flex:1">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                            <h3 style="margin:0;font-size:16px">Запчасти (${partsData.total||0})</h3>
                            <button class="btn btn-sm btn-primary" id="btn-add-part">
                                <span class="material-symbols-outlined" style="font-size:16px">add</span>
                            </button>
                        </div>
                        <div class="card" style="max-height:500px;overflow-y:auto;padding:12px">
                            ${Object.keys(clusters).map(cluster => `
                                <div style="margin-bottom:12px">
                                    <div style="margin-bottom:6px">
                                        <span class="cluster-badge" style="background:${clusterColors[cluster]||'#64748b'}20;color:${clusterColors[cluster]||'#64748b'}">${cluster} (${clusters[cluster].length})</span>
                                    </div>
                                    ${clusters[cluster].map(p => `
                                        <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 8px;border-radius:4px;font-size:13px" class="part-row">
                                            <span>${p.name_ru || p.name}</span>
                                            <button class="btn btn-sm" style="opacity:0.3;padding:2px" onclick="deletePart(${p.id})"><span class="material-symbols-outlined" style="font-size:14px">close</span></button>
                                        </div>
                                    `).join('')}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;

            // Seed button
            document.getElementById('btn-seed-catalog')?.addEventListener('click', async () => {
                const btn = document.getElementById('btn-seed-catalog');
                btn.disabled = true; btn.textContent = 'Загрузка...';
                try {
                    const r = await api.post('/api/promotion/seed-catalog', {});
                    showToast(`Загружено: ${r.brands||0} марок, ${r.models||0} моделей, ${r.parts||0} категорий`, 'success');
                    window._promTab = 'catalog'; renderPromotion(container);
                } catch (e) { showToast('Ошибка: ' + e.message, 'error'); btn.disabled = false; }
            });

            // Add brand
            document.getElementById('btn-add-brand')?.addEventListener('click', () => {
                const name = prompt('Название марки (англ):');
                if (!name) return;
                const nameRu = prompt('Название по-русски (необязательно):') || '';
                api.post('/api/promotion/brands', { name, name_ru: nameRu })
                    .then(() => { showToast('Марка добавлена', 'success'); window._promTab = 'catalog'; renderPromotion(container); })
                    .catch(e => showToast('Ошибка: ' + e.message, 'error'));
            });

            // Add part
            document.getElementById('btn-add-part')?.addEventListener('click', () => {
                const name = prompt('Название запчасти:');
                if (!name) return;
                const cluster = prompt('Кластер (тормоза/подвеска/привод/двигатель/фильтры/электрика/кузов/выхлоп):') || '';
                api.post('/api/promotion/parts', { name, name_ru: name, cluster })
                    .then(() => { showToast('Категория добавлена', 'success'); window._promTab = 'catalog'; renderPromotion(container); })
                    .catch(e => showToast('Ошибка: ' + e.message, 'error'));
            });

            // Brand row click — show models
            document.querySelectorAll('.brand-row').forEach(row => {
                row.addEventListener('click', async () => {
                    const brandId = row.dataset.brandId;
                    document.querySelectorAll('.brand-row').forEach(r => r.style.background = '');
                    row.style.background = 'var(--bg-input)';
                    const panel = document.getElementById('brand-models-panel');
                    panel.innerHTML = '<div class="spinner" style="margin:12px auto"></div>';
                    try {
                        const data = await api.get(`/api/promotion/brands/${brandId}/models`);
                        panel.innerHTML = `
                            <div class="card" style="padding:16px">
                                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                                    <h4 style="margin:0;font-size:14px">${data.brand.name} — модели (${data.total})</h4>
                                    <button class="btn btn-sm btn-primary" id="btn-add-model"><span class="material-symbols-outlined" style="font-size:16px">add</span> Модель</button>
                                </div>
                                <div style="display:flex;flex-wrap:wrap;gap:6px">
                                    ${data.models.map(m => `
                                        <div class="brand-chip" title="${m.name_ru}">
                                            ${m.popular ? '<span class="material-symbols-outlined" style="font-size:12px;color:var(--warning)">star</span>' : ''}
                                            ${m.name}
                                            <span class="material-symbols-outlined" style="font-size:12px;opacity:0.3;cursor:pointer" onclick="event.stopPropagation();deleteModel(${m.id})">close</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                        document.getElementById('btn-add-model')?.addEventListener('click', () => {
                            const name = prompt('Название модели:');
                            if (!name) return;
                            api.post(`/api/promotion/brands/${brandId}/models`, { name, name_ru: '', popular: false })
                                .then(() => { showToast('Модель добавлена', 'success'); row.click(); })
                                .catch(e => showToast('Ошибка: ' + e.message, 'error'));
                        });
                    } catch (e) { panel.innerHTML = `<p style="color:var(--danger)">Ошибка: ${e.message}</p>`; }
                });
            });

        } catch (e) {
            tabEl.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Ошибка загрузки: ${e.message}</p></div>`;
        }
    }

    // ── Tab: Keywords ──
    async function renderKeywordsTab(tabEl) {
        tabEl.innerHTML = '<div class="spinner"></div>';
        try {
            const [preview, progress] = await Promise.all([
                api.get('/api/promotion/keywords/preview'),
                api.get('/api/promotion/campaigns/batch/progress'),
            ]);
            const totals = preview.totals || {};
            const brands = preview.brands || [];
            const isRunning = progress.running;

            tabEl.innerHTML = `
                <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:20px">
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Всего кампаний</div><div class="kpi-value" style="font-size:20px">${totals.campaigns||0}</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Групп объявлений</div><div class="kpi-value" style="font-size:20px">${(totals.groups||0).toLocaleString()}</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Ключевых фраз</div><div class="kpi-value" style="font-size:20px">${(totals.keywords||0).toLocaleString()}</div></div>
                    <div class="kpi-card" style="padding:14px"><div class="kpi-label">Марок</div><div class="kpi-value" style="font-size:20px">${totals.brands||0}</div></div>
                </div>

                ${isRunning ? `
                <!-- Active batch progress -->
                <div class="card" style="padding:20px;margin-bottom:16px;border:2px solid var(--primary)">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                        <h3 style="margin:0;font-size:15px;color:var(--primary)">
                            <span class="material-symbols-outlined" style="font-size:18px;animation:spin 1s linear infinite">progress_activity</span>
                            Создание кампаний...
                        </h3>
                        <span style="font-size:13px;color:var(--text-muted)">${progress.brands_done||0}/${progress.brands_total||0} марок</span>
                    </div>
                    <div style="background:var(--bg-input);border-radius:8px;height:8px;margin-bottom:12px;overflow:hidden">
                        <div style="width:${progress.brands_total ? (progress.brands_done/progress.brands_total*100) : 0}%;height:100%;background:var(--primary);border-radius:8px;transition:width 0.5s"></div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px;font-size:13px">
                        <div><span style="color:var(--text-muted)">Марка:</span> <b>${progress.current_brand||'—'}</b></div>
                        <div><span style="color:var(--text-muted)">Кампаний:</span> <b>${progress.campaigns_created||0}</b></div>
                        <div><span style="color:var(--text-muted)">Групп:</span> <b>${progress.groups_created||0}</b></div>
                        <div><span style="color:var(--text-muted)">Ключевиков:</span> <b>${progress.keywords_added||0}</b></div>
                    </div>
                    <div style="font-size:12px;color:var(--text-secondary);max-height:120px;overflow-y:auto;background:var(--bg-input);border-radius:6px;padding:8px;font-family:monospace">
                        ${(progress.log||[]).slice(-10).map(l => `<div>${l}</div>`).join('')}
                    </div>
                    ${progress.errors?.length ? `<div style="margin-top:8px;color:var(--danger);font-size:12px">${progress.errors.length} ошибок</div>` : ''}
                </div>` : ''}

                <!-- Batch creation controls -->
                <div class="card" style="padding:16px;margin-bottom:16px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                        <h3 style="margin:0;font-size:15px">Создание кампаний</h3>
                        <div style="display:flex;gap:8px;align-items:center">
                            <div style="display:flex;align-items:center;gap:6px;font-size:13px">
                                <label>Бюджет/день:</label>
                                <input type="number" id="batch-budget" value="300" min="300" step="50" style="width:80px;padding:4px 8px;border:1px solid var(--border);border-radius:6px;font-size:13px;background:var(--bg-input);color:var(--text-primary)"> ₽
                            </div>
                            <div style="display:flex;gap:4px">
                                <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="geo-msk" checked> МСК+СПб</label>
                                <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="geo-regions" checked> Регионы</label>
                            </div>
                            <button class="btn btn-primary" id="btn-batch-create" ${isRunning ? 'disabled' : ''}>
                                <span class="material-symbols-outlined" style="font-size:16px">rocket_launch</span>
                                Создать выбранные
                            </button>
                        </div>
                    </div>

                    <div style="margin-bottom:8px;display:flex;gap:8px;justify-content:space-between;align-items:center">
                        <div style="display:flex;gap:8px">
                            <button class="btn btn-sm btn-secondary" id="btn-select-all">Выбрать все</button>
                            <button class="btn btn-sm btn-secondary" id="btn-select-popular">Только ТОП-5</button>
                            <button class="btn btn-sm btn-secondary" id="btn-deselect-all">Сбросить</button>
                        </div>
                        <span style="font-size:12px;color:var(--text-muted)" id="selected-count">Выбрано: 0</span>
                    </div>

                    <table class="data-table">
                        <thead><tr><th style="width:40px"></th><th>Марка</th><th>Моделей</th><th>Групп</th><th>Ключевиков</th><th></th></tr></thead>
                        <tbody>
                            ${brands.map(b => `<tr>
                                <td><input type="checkbox" class="brand-check" data-brand-id="${b.brand_id}" value="${b.brand_id}"></td>
                                <td style="font-weight:600">${b.brand}</td>
                                <td>${b.models}</td>
                                <td>${b.groups}</td>
                                <td style="font-weight:600;color:var(--primary)">${b.keywords.toLocaleString()}</td>
                                <td><button class="btn btn-sm btn-secondary" onclick="previewBrandKeywords(${b.brand_id}, '${b.brand}')"><span class="material-symbols-outlined" style="font-size:16px">visibility</span></button></td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>

                <!-- Preview area -->
                <div id="kw-preview-area"></div>
            `;

            // Update selected count
            const updateCount = () => {
                const checked = document.querySelectorAll('.brand-check:checked').length;
                const el = document.getElementById('selected-count');
                if (el) el.textContent = 'Выбрано: ' + checked;
            };
            document.querySelectorAll('.brand-check').forEach(cb => cb.addEventListener('change', updateCount));

            // Select all / popular / deselect
            document.getElementById('btn-select-all')?.addEventListener('click', () => {
                document.querySelectorAll('.brand-check').forEach(cb => cb.checked = true);
                updateCount();
            });
            document.getElementById('btn-deselect-all')?.addEventListener('click', () => {
                document.querySelectorAll('.brand-check').forEach(cb => cb.checked = false);
                updateCount();
            });
            document.getElementById('btn-select-popular')?.addEventListener('click', () => {
                document.querySelectorAll('.brand-check').forEach(cb => cb.checked = false);
                const topBrands = brands.sort((a,b) => b.models - a.models).slice(0, 5);
                topBrands.forEach(b => {
                    const cb = document.querySelector(`.brand-check[data-brand-id="${b.brand_id}"]`);
                    if (cb) cb.checked = true;
                });
                updateCount();
            });

            // Batch create
            document.getElementById('btn-batch-create')?.addEventListener('click', async () => {
                const selectedIds = [...document.querySelectorAll('.brand-check:checked')].map(cb => parseInt(cb.value));
                if (!selectedIds.length) { showToast('Выберите хотя бы одну марку', 'warning'); return; }
                
                const budget = parseFloat(document.getElementById('batch-budget').value) || 150;
                const geoSegments = [];
                if (document.getElementById('geo-msk')?.checked) geoSegments.push('msk_spb');
                if (document.getElementById('geo-regions')?.checked) geoSegments.push('regions');
                if (!geoSegments.length) { showToast('Выберите хотя бы один гео-сегмент', 'warning'); return; }

                const totalCamps = selectedIds.length * geoSegments.length;
                if (!confirm(`Создать ${totalCamps} кампаний для ${selectedIds.length} марок?\n\nБюджет: ${budget} ₽/день на кампанию\nГео: ${geoSegments.join(', ')}`)) return;

                const btn = document.getElementById('btn-batch-create');
                btn.disabled = true;
                btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;margin:0;border-width:2px"></div> Запуск...';

                try {
                    await api.post('/api/promotion/campaigns/batch', {
                        brand_ids: selectedIds,
                        geo_segments: geoSegments,
                        daily_budget: budget,
                    });
                    showToast('Создание запущено!', 'success');
                    // Start polling progress
                    const pollInterval = setInterval(async () => {
                        try {
                            const p = await api.get('/api/promotion/campaigns/batch/progress');
                            if (!p.running) {
                                clearInterval(pollInterval);
                                showToast(`Готово! Кампаний: ${p.campaigns_created}, Групп: ${p.groups_created}, Ключевиков: ${p.keywords_added}`, 'success');
                                window._promTab = 'keywords';
                                renderPromotion(container);
                            } else {
                                window._promTab = 'keywords';
                                renderPromotion(container);
                            }
                        } catch (e) { clearInterval(pollInterval); }
                    }, 3000);
                } catch (e) {
                    showToast('Ошибка: ' + e.message, 'error');
                    btn.disabled = false;
                    btn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px">rocket_launch</span> Создать выбранные';
                }
            });

        } catch (e) {
            tabEl.innerHTML = `<div class="empty-state"><span class="material-symbols-outlined">error</span><p>Справочник пуст. Сначала загрузите данные во вкладке «Справочник».</p></div>`;
        }
    }

    // Global helpers for catalog
    window.deleteBrand = async (id) => {
        if (!confirm('Удалить марку и все её модели?')) return;
        try { await api.del(`/api/promotion/brands/${id}`); showToast('Удалено', 'success'); window._promTab = 'catalog'; renderPromotion(container); }
        catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
    };
    window.deleteModel = async (id) => {
        if (!confirm('Удалить модель?')) return;
        try { await api.del(`/api/promotion/models/${id}`); showToast('Удалено', 'success'); window._promTab = 'catalog'; renderPromotion(container); }
        catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
    };
    window.deletePart = async (id) => {
        if (!confirm('Удалить категорию?')) return;
        try { await api.del(`/api/promotion/parts/${id}`); showToast('Удалено', 'success'); window._promTab = 'catalog'; renderPromotion(container); }
        catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
    };
    window.previewBrandKeywords = async (brandId, brandName) => {
        const area = document.getElementById('kw-preview-area');
        if (!area) return;
        area.innerHTML = '<div class="spinner" style="margin:20px auto"></div>';
        try {
            const data = await api.get(`/api/promotion/keywords/generate/${brandId}`);
            area.innerHTML = `
                <div class="card" style="padding:16px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                        <h3 style="margin:0;font-size:15px">${brandName}: ${data.total_groups} групп, ${data.total_keywords.toLocaleString()} ключевиков</h3>
                        <button class="btn btn-sm btn-secondary" onclick="document.getElementById('kw-preview-area').innerHTML=''">
                            <span class="material-symbols-outlined" style="font-size:16px">close</span>
                        </button>
                    </div>
                    <div style="max-height:400px;overflow-y:auto">
                        ${data.groups.slice(0, 20).map(g => `
                            <details style="margin-bottom:8px;border:1px solid var(--border);border-radius:8px;padding:8px 12px">
                                <summary style="cursor:pointer;font-weight:500;font-size:13px;display:flex;justify-content:space-between;align-items:center">
                                    <span>${g.name}</span>
                                    <span style="font-size:12px;color:var(--text-muted)">${g.autotarget ? 'автотаргет' : g.keywords.length + ' ключей'}</span>
                                </summary>
                                ${g.autotarget ? '<p style="font-size:12px;color:var(--text-muted);margin:8px 0 0">Без ключевых слов — автотаргет Яндекса</p>' : `
                                <div style="margin-top:8px;font-size:12px;color:var(--text-secondary);line-height:1.8">
                                    ${g.keywords.map(k => `<div style="padding:2px 0;border-bottom:1px solid var(--border)">${k}</div>`).join('')}
                                </div>`}
                                <div style="margin-top:8px">
                                    ${g.ads.map(a => `
                                        <div style="background:var(--bg-input);border-radius:6px;padding:8px;margin-bottom:6px;font-size:12px">
                                            <div style="color:var(--primary);font-weight:600">${a.title1}</div>
                                            <div style="color:var(--success);font-size:11px">${a.title2}</div>
                                            <div style="color:var(--text-secondary)">${a.text}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </details>
                        `).join('')}
                        ${data.groups.length > 20 ? `<p style="text-align:center;color:var(--text-muted);font-size:13px">... и ещё ${data.groups.length - 20} групп</p>` : ''}
                    </div>
                </div>
            `;
        } catch (e) { area.innerHTML = `<p style="color:var(--danger)">Ошибка: ${e.message}</p>`; }
    };

    // ── Tab switching ──
    const tabContent = document.getElementById('prom-tab-content');
    document.querySelectorAll('.prom-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.prom-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const tabName = tab.dataset.tab;
            window._promTab = tabName;
            if (tabName === 'campaigns') renderCampaignsTab(tabContent);
            else if (tabName === 'catalog') renderCatalogTab(tabContent);
            else if (tabName === 'keywords') renderKeywordsTab(tabContent);
        });
    });

    // Render active tab
    if (activePromTab === 'campaigns') renderCampaignsTab(tabContent);
    else if (activePromTab === 'catalog') renderCatalogTab(tabContent);
    else if (activePromTab === 'keywords') renderKeywordsTab(tabContent);

    // Disconnect handler
    document.getElementById('btn-yd-disconnect')?.addEventListener('click', async () => {
        if (!confirm('Отключить Яндекс.Директ?')) return;
        try { await api.del('/api/promotion/config'); showToast('Отключён', 'success'); setTimeout(() => renderPromotion(container), 300); }
        catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
    });
}

function showEnableCampaignModal(container) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>Новая рекламная кампания</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Название кампании</label>
                    <input class="form-input" id="yd-camp-name" value="Запчасти — Umit">
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label class="form-label">Дневной бюджет</label>
                        <div class="form-input-suffix">
                            <input class="form-input" type="number" id="yd-camp-budget" value="300" min="100" step="50">
                            <span class="suffix">₽/день</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Регион</label>
                        <select class="form-input" id="yd-camp-region">
                            <option value="225" selected>Россия</option>
                            <option value="1">Москва и МО</option>
                            <option value="10174">Санкт-Петербург и ЛО</option>
                            <option value="11079">Урал</option>
                            <option value="11111">Сибирь</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Ключевые слова</label>
                    <p class="form-hint">По одному на строку.</p>
                    <textarea class="form-input" id="yd-camp-keywords" rows="4" style="font-size:13px">запчасти оптом
запчасти для спецтехники
купить запчасти
заказать запчасти</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Отмена</button>
                <button class="btn btn-primary" id="btn-yd-create-campaign">
                    <span class="material-symbols-outlined">rocket_launch</span> Запустить
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('btn-yd-create-campaign')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-yd-create-campaign');
        btn.disabled = true;
        btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;margin:0;border-width:2px"></div> Создание...';

        const name = document.getElementById('yd-camp-name').value.trim() || 'Запчасти — Umit';
        const budget = parseFloat(document.getElementById('yd-camp-budget').value) || 300;
        const region = parseInt(document.getElementById('yd-camp-region').value) || 225;
        const keywords = document.getElementById('yd-camp-keywords').value.split('\n').map(s => s.trim()).filter(Boolean);

        try {
            const result = await api.post('/api/promotion/campaigns/enable', {
                name, daily_budget: budget, keywords, regions: [region],
            });
            showToast(result.message, 'success');
            overlay.remove();
            setTimeout(() => renderPromotion(container), 500);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined">rocket_launch</span> Запустить';
        }
    });
}

window.ydPauseCampaign = async function(id) {
    if (!confirm('Приостановить кампанию?')) return;
    try {
        const r = await api.post(`/api/promotion/campaigns/${id}/pause`, {});
        showToast(r.message, 'success');
        handleRoute();
    } catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
};

window.ydResumeCampaign = async function(id) {
    try {
        const r = await api.post(`/api/promotion/campaigns/${id}/resume`, {});
        showToast(r.message, 'success');
        handleRoute();
    } catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
};

// ══════════════════════════════════════════
//  PAGE: Telegram Mailing
// ══════════════════════════════════════════

function tgStatusBadge(status) {
    const labels = {
        draft: 'Черновик', sending: 'Отправка', paused: 'Пауза',
        completed: 'Завершена', cancelled: 'Отменена',
    };
    const cls = {
        draft: 'pending', sending: 'distributing', paused: 'waiting',
        completed: 'fully_notified', cancelled: 'failed',
    };
    return `<span class="badge ${cls[status] || status}">${labels[status] || status}</span>`;
}

let tgPage = 1;

async function renderTelegram(container) {
    const [data, tgStatus] = await Promise.all([
        api.get(`/api/telegram/campaigns?page=${tgPage}&page_size=20`),
        api.get('/api/telegram/status').catch(() => ({ connected: false })),
    ]);

    const parser = tgStatus.parser || {};
    const senders = tgStatus.senders || [];

    container.innerHTML = `
        <div class="action-bar">
            <div style="display:flex;align-items:center;gap:12px">
                <span style="font-size:13px;color:var(--text-secondary)">Кампаний: <strong>${data.total}</strong></span>
                <span style="font-size:13px;color:var(--text-secondary)">Пропускная способность: <strong>${tgStatus.daily_capacity || 0}</strong> сообщений/день</span>
            </div>
            <button class="btn btn-primary" id="btn-new-tg-campaign">
                <span class="material-symbols-outlined">add</span> Новая TG-кампания
            </button>
        </div>

        <!-- Accounts -->
        <div class="card mb-24" style="padding:16px 20px">
            <h4 style="margin:0 0 12px;font-size:14px;display:flex;align-items:center;gap:6px">
                <span class="material-symbols-outlined" style="font-size:18px">group</span>
                Аккаунты Telegram
            </h4>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">
                <!-- Parser -->
                <div style="padding:12px;border-radius:8px;border:1px solid rgba(245,158,11,0.3);background:rgba(245,158,11,0.05)">
                    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                        <span class="status-dot ${parser.connected ? 'online' : ''}"></span>
                        <span style="font-size:12px;font-weight:600;color:#f59e0b">🔍 ПАРСЕР</span>
                        ${parser.connected ? `<span class="material-symbols-outlined tg-rename-btn" data-session="${parser.session_name || ''}" data-name="${parser.user?.first_name || ''}" data-last="${parser.user?.last_name || ''}" style="font-size:14px;cursor:pointer;margin-left:auto;color:var(--text-muted)" title="Переименовать">edit</span>` : ''}
                    </div>
                    ${parser.user ? `
                        <div style="font-size:13px;font-weight:500">${parser.user.first_name || ''} ${parser.user.last_name || ''}</div>
                        <div style="font-size:11px;color:var(--text-muted)">${parser.user.phone || ''}</div>
                    ` : '<div style="font-size:12px;color:var(--text-muted)">Не подключен</div>'}
                    <div style="margin-top:6px;padding:4px 8px;background:rgba(245,158,11,0.1);border-radius:4px;font-size:10px;color:#92600a;line-height:1.4">
                        ⚠️ Добавьте этот аккаунт <strong>админом</strong> в канал для загрузки подписчиков
                    </div>
                </div>
                <!-- Senders -->
                ${senders.map((s, i) => `
                    <div style="padding:12px;border-radius:8px;border:1px solid ${s.connected ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};background:${s.connected ? 'rgba(16,185,129,0.05)' : 'rgba(239,68,68,0.05)'}">
                        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                            <span class="status-dot ${s.connected ? 'online' : ''}"></span>
                            <span style="font-size:12px;font-weight:600;color:${s.connected ? '#10b981' : '#ef4444'}">📤 Отправитель ${i + 1}</span>
                            ${s.connected ? `<span class="material-symbols-outlined tg-rename-btn" data-session="${s.session_name}" data-name="${s.user_info?.first_name || ''}" data-last="${s.user_info?.last_name || ''}" style="font-size:14px;cursor:pointer;margin-left:auto;color:var(--text-muted)" title="Переименовать">edit</span>` : ''}
                        </div>
                        ${s.user_info ? `
                            <div style="font-size:13px;font-weight:500">${s.user_info.first_name || ''} ${s.user_info.last_name || ''}</div>
                            <div style="font-size:11px;color:var(--text-muted)">${s.user_info.phone || ''}</div>
                        ` : '<div style="font-size:12px;color:var(--text-muted)">Не подключен</div>'}
                        <div style="margin-top:4px;font-size:10px;color:var(--text-muted)">Лимит: 15 сообщ./день</div>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- Instructions -->
        <div class="card mb-24" style="padding:16px 20px;background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.06));border:1px solid rgba(99,102,241,0.15)">
            <div style="display:flex;gap:12px;align-items:flex-start">
                <span class="material-symbols-outlined" style="color:var(--primary);font-size:24px;margin-top:2px">info</span>
                <div style="font-size:13px;line-height:1.6;color:var(--text-secondary)">
                    <strong style="color:var(--text);font-size:14px">📋 Как работает TG-рассылка</strong><br>
                    <div style="margin-top:8px;display:grid;gap:6px">
                        <div>1️⃣ <strong>Создайте кампанию</strong> — укажите название, текст сообщения и канал-источник подписчиков</div>
                        <div>2️⃣ <strong>Загрузите подписчиков</strong> — нажмите кнопку на странице кампании для загрузки списка</div>
                        <div>3️⃣ <strong>Запустите рассылку</strong> — юзербот отправит сообщения каждому в ЛС с заданной задержкой</div>
                    </div>
                    <div style="margin-top:10px;padding:8px 12px;background:rgba(245,158,11,0.1);border-radius:6px;border-left:3px solid #f59e0b">
                        <strong style="color:#f59e0b">⚠️ Важно:</strong> Для загрузки подписчиков из канала юзербот-аккаунт должен быть <strong>администратором</strong> этого канала. Без прав админа Telegram не отдаёт список участников.
                    </div>
                    <div style="margin-top:8px;padding:8px 12px;background:rgba(239,68,68,0.08);border-radius:6px;border-left:3px solid #ef4444">
                        <strong style="color:#ef4444">🛡️ Жёсткие лимиты:</strong> Максимум <strong>15 сообщений за 24 часа</strong> (новый аккаунт). Мин. задержка <strong>35 сек</strong>. При достижении лимита рассылка авто-пауза.
                    </div>
                    <div style="margin-top:8px;padding:8px 12px;background:rgba(168,85,247,0.08);border-radius:6px;border-left:3px solid #a855f7">
                        <strong style="color:#a855f7">📨 Жалобы на спам:</strong> Получатели могут нажать «Пожаловаться на спам» — <strong>4-5 жалоб = временный бан, 10+ = перманентный бан</strong>. Пишите полезный контент, не агрессивную рекламу!
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Название</th>
                        <th>Канал</th>
                        <th>Статус</th>
                        <th>Прогресс</th>
                        <th>Отправлено</th>
                        <th>Ошибки</th>
                        <th>Дата</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.items.length === 0 ? '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-muted)">Нет TG-кампаний. Создайте первую!</td></tr>' : ''}
                    ${data.items.map(c => `
                        <tr>
                            <td><a href="#/telegram/${c.id}" style="color:var(--primary);font-weight:600;text-decoration:none">#${c.id}</a></td>
                            <td style="font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${c.name}">${c.name}</td>
                            <td style="color:var(--text-secondary);font-size:13px">${c.source_channel || '—'}</td>
                            <td>${tgStatusBadge(c.status)}</td>
                            <td>
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div style="flex:1;height:6px;background:var(--bg-input);border-radius:3px;overflow:hidden">
                                        <div style="height:100%;width:${c.progress}%;background:${c.status === 'completed' ? 'var(--success)' : 'var(--primary)'};border-radius:3px;transition:width 0.3s"></div>
                                    </div>
                                    <span style="font-size:12px;color:var(--text-muted);min-width:32px">${c.progress}%</span>
                                </div>
                            </td>
                            <td style="text-align:center;color:var(--success)">${c.sent_count}</td>
                            <td style="text-align:center;color:${c.failed_count > 0 ? 'var(--danger)' : 'var(--text-muted)'}">${c.failed_count}</td>
                            <td style="color:var(--text-muted);font-size:12px">${timeAgo(c.created_at)}</td>
                            <td>
                                <div style="display:flex;gap:4px">
                                    ${c.status === 'draft' || c.status === 'paused' ? `<button class="btn btn-sm btn-primary" onclick="tgSendCampaign(${c.id})" title="Запустить"><span class="material-symbols-outlined" style="font-size:16px">play_arrow</span></button>` : ''}
                                    ${c.status === 'sending' ? `<button class="btn btn-sm btn-secondary" onclick="tgPauseCampaign(${c.id})" title="Пауза"><span class="material-symbols-outlined" style="font-size:16px">pause</span></button>` : ''}
                                    ${c.status !== 'sending' ? `<button class="btn btn-sm btn-danger" onclick="tgDeleteCampaign(${c.id})" title="Удалить"><span class="material-symbols-outlined" style="font-size:16px">delete</span></button>` : ''}
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <div class="pagination" id="tg-pagination"></div>
    `;

    const totalPages = Math.ceil(data.total / 20);
    renderPagination('tg-pagination', tgPage, totalPages, (p) => { tgPage = p; renderTelegram(container); });

    document.getElementById('btn-new-tg-campaign').addEventListener('click', () => showCreateTgCampaignModal(container));

    // Rename buttons
    document.querySelectorAll('.tg-rename-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const session = btn.dataset.session;
            const currentName = btn.dataset.name;
            const currentLast = btn.dataset.last;
            const input = prompt('Введите новое имя (Имя Фамилия):', `${currentName} ${currentLast}`.trim());
            if (!input) return;
            const parts = input.trim().split(/\s+/);
            const firstName = parts[0] || '';
            const lastName = parts.slice(1).join(' ') || '';
            try {
                const r = await api.post('/api/telegram/accounts/rename', { session_name: session, first_name: firstName, last_name: lastName });
                showToast(r.message, 'success');
                await renderTelegram(container);
            } catch (e) {
                showToast('Ошибка: ' + e.message, 'error');
            }
        });
    });
}

function showCreateTgCampaignModal(container) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal" style="max-width:560px">
            <div class="modal-header">
                <h3>Новая TG-кампания</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Название кампании *</label>
                    <input class="form-input" id="tg-name" placeholder="Промо-рассылка март">
                </div>
                <div class="form-group">
                    <label class="form-label">Канал-источник подписчиков</label>
                    <p class="form-hint">Укажите @username или числовой ID канала. Подписчиков можно загрузить кнопкой на странице кампании.</p>
                    <input class="form-input" id="tg-channel" placeholder="@my_channel или -1001234567890">
                    <div style="margin-top:8px;padding:8px 12px;background:rgba(245,158,11,0.1);border-radius:6px;font-size:12px;line-height:1.5;color:#92600a">
                        <strong>⚠️ Требования к каналу:</strong><br>
                        • Юзербот-аккаунт должен быть <strong>администратором</strong> канала<br>
                        • Без прав админа невозможно получить список подписчиков<br>
                        • Для приватных каналов используйте числовой ID (начинается с -100)
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Текст сообщения *</label>
                    <p class="form-hint">Поддерживается Markdown-форматирование Telegram. Лимит подписи к фото: 1024 символа.</p>
                    <textarea class="form-input" id="tg-message" rows="6" placeholder="Привет! 👋\n\nМы предлагаем..." oninput="document.getElementById('tg-char-count').textContent=this.value.length"></textarea>
                    <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:12px">
                        <span id="tg-char-count" style="color:var(--text-muted)">0</span>
                        <span style="color:var(--text-muted)">символов (макс. 4096, подпись к фото макс. 1024)</span>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Задержка между сообщениями</label>
                    <div style="margin-top:8px">
                        <input class="form-input" type="number" id="tg-delay" value="60" min="35" max="300">
                        <span class="suffix" style="font-size:12px;color:var(--text-muted);margin-left:6px">секунд (мин. 35, рекомендуемо 60)</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Отмена</button>
                <button class="btn btn-primary" id="btn-save-tg-campaign">
                    <span class="material-symbols-outlined">add</span> Создать
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('btn-save-tg-campaign').addEventListener('click', async () => {
        const name = document.getElementById('tg-name').value.trim();
        const message_text = document.getElementById('tg-message').value.trim();
        if (!name) return showToast('Укажите название', 'error');
        if (!message_text) return showToast('Укажите текст сообщения', 'error');

        try {
            const result = await api.post('/api/telegram/campaigns', {
                name,
                message_text,
                source_channel: document.getElementById('tg-channel').value.trim(),
                delay_seconds: parseInt(document.getElementById('tg-delay').value) || 35,
            });
            overlay.remove();
            showToast(result.message, 'success');
            navigateTo(`/telegram/${result.id}`);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });
}

async function renderTgCampaignDetail(container, campaignId) {
    const c = await api.get(`/api/telegram/campaigns/${campaignId}`);

    const progress = c.total_recipients > 0 ? Math.round((c.sent_count + c.failed_count) / c.total_recipients * 100) : 0;

    container.innerHTML = `
        <div style="margin-bottom:16px">
            <a href="#/telegram" style="color:var(--primary);text-decoration:none;font-size:13px;display:inline-flex;align-items:center;gap:4px">
                <span class="material-symbols-outlined" style="font-size:18px">arrow_back</span> Назад к списку
            </a>
        </div>

        <div class="card mb-24" style="padding:24px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px">
                <div>
                    <h2 style="margin:0 0 4px;font-size:20px">${c.name}</h2>
                    <div style="display:flex;gap:12px;align-items:center">
                        ${tgStatusBadge(c.status)}
                        ${c.source_channel ? `<span style="font-size:13px;color:var(--text-muted)">Канал: ${c.source_channel}</span>` : ''}
                        <span style="font-size:13px;color:var(--text-muted)">Задержка: ${c.delay_seconds}с</span>
                    </div>
                </div>
                <div style="display:flex;gap:8px">
                    ${c.source_channel && (c.status === 'draft') ? `<button class="btn btn-secondary" id="btn-tg-fetch">
                        <span class="material-symbols-outlined">download</span> Загрузить подписчиков
                    </button>` : ''}
                    ${!c.source_channel && (c.status === 'draft') ? `<span style="font-size:12px;color:var(--text-muted);padding:8px">Канал не указан — добавьте получателей вручную</span>` : ''}
                    ${c.status === 'draft' || c.status === 'paused' ? `<button class="btn btn-primary" id="btn-tg-send">
                        <span class="material-symbols-outlined">play_arrow</span> Запустить
                    </button>` : ''}
                    ${c.status === 'sending' ? `<button class="btn btn-secondary" id="btn-tg-pause">
                        <span class="material-symbols-outlined">pause</span> Пауза
                    </button>` : ''}
                    ${c.status === 'sending' || c.status === 'paused' ? `<button class="btn btn-danger" id="btn-tg-cancel">
                        <span class="material-symbols-outlined">cancel</span> Отменить
                    </button>` : ''}
                </div>
            </div>

            <!-- Stats -->
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px">
                <div style="padding:12px;background:var(--bg-input);border-radius:8px;text-align:center">
                    <div style="font-size:24px;font-weight:700">${c.total_recipients}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Всего</div>
                </div>
                <div style="padding:12px;background:var(--bg-input);border-radius:8px;text-align:center">
                    <div style="font-size:24px;font-weight:700;color:var(--success)">${c.sent_count}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Отправлено</div>
                </div>
                <div style="padding:12px;background:var(--bg-input);border-radius:8px;text-align:center">
                    <div style="font-size:24px;font-weight:700;color:${c.failed_count > 0 ? 'var(--danger)' : 'var(--text-muted)'}">${c.failed_count}</div>
                    <div style="font-size:12px;color:var(--text-muted)">Ошибки</div>
                </div>
                <div style="padding:12px;background:var(--bg-input);border-radius:8px;text-align:center">
                    <div style="font-size:24px;font-weight:700;color:var(--primary)">${progress}%</div>
                    <div style="font-size:12px;color:var(--text-muted)">Прогресс</div>
                </div>
            </div>

            <!-- Progress bar -->
            <div style="height:8px;background:var(--bg-input);border-radius:4px;overflow:hidden;margin-bottom:20px">
                <div style="height:100%;width:${progress}%;background:linear-gradient(90deg,var(--primary),#8b5cf6);border-radius:4px;transition:width 0.5s"></div>
            </div>

            <!-- Message preview -->
            <div style="margin-bottom:16px">
                <h4 style="margin:0 0 8px;font-size:14px;color:var(--text-secondary)">Текст сообщения: <span style="font-weight:400;font-size:12px;color:var(--text-muted)">${(c.message_text || '').length} символов</span></h4>
                <div style="padding:16px;background:var(--bg-input);border-radius:8px;white-space:pre-wrap;font-size:14px;line-height:1.5;max-height:200px;overflow-y:auto">${c.message_text || '<span style="color:var(--text-muted)">Не задан</span>'}</div>
            </div>

            <!-- Image -->
            <div style="margin-bottom:16px">
                <h4 style="margin:0 0 8px;font-size:14px;color:var(--text-secondary)">Изображение:</h4>
                ${c.image_path ? `
                    <div style="display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg-input);border-radius:8px">
                        <span class="material-symbols-outlined" style="color:var(--success);font-size:20px">image</span>
                        <span style="font-size:13px;flex:1">Изображение прикреплено ✔️</span>
                        ${c.status === 'draft' ? '<button class="btn btn-sm btn-danger" id="btn-tg-del-image"><span class="material-symbols-outlined" style="font-size:14px">delete</span> Удалить</button>' : ''}
                    </div>
                ` : `
                    <div style="padding:12px;background:var(--bg-input);border-radius:8px">
                        ${c.status === 'draft' ? `
                            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--primary);font-size:13px">
                                <span class="material-symbols-outlined">upload</span>
                                Загрузить изображение (JPG, PNG, GIF, макс. 5 МБ)
                                <input type="file" id="tg-image-input" accept=".jpg,.jpeg,.png,.gif,.webp" style="display:none">
                            </label>
                        ` : '<span style="font-size:13px;color:var(--text-muted)">Нет изображения</span>'}
                    </div>
                `}
            </div>
        </div>

        <!-- Recipients table -->
        <div class="card">
            <div class="card-header">
                <h3>Получатели (${c.recipients.length})</h3>
                <span id="tg-selected-count" style="font-size:12px;color:var(--text-muted);margin-left:8px"></span>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width:36px;text-align:center"><input type="checkbox" id="tg-select-all" checked title="Выбрать все / Снять все"></th>
                        <th>TG User ID</th>
                        <th>Username</th>
                        <th>Имя</th>
                        <th>Статус</th>
                        <th>Ошибка</th>
                        <th>Отправлено</th>
                    </tr>
                </thead>
                <tbody>
                    ${c.recipients.length === 0 ? '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted)">Нет получателей. Загрузите подписчиков из канала.</td></tr>' : ''}
                    ${c.recipients.map(r => {
                        const statusCls = r.status === 'sent' ? 'fully_notified' : r.status === 'failed' || r.status === 'blocked' ? 'failed' : 'pending';
                        const statusLabel = {pending: 'Ожидание', sent: 'Отправлено', failed: 'Ошибка', blocked: 'Заблокирован', skipped: 'Пропущен'};
                        const canSelect = r.status === 'pending';
                        return `
                        <tr>
                            <td style="text-align:center">${canSelect ? `<input type="checkbox" class="tg-rcpt-cb" data-id="${r.id}" checked>` : '<span style="color:var(--text-muted)">—</span>'}</td>
                            <td style="font-family:monospace;font-size:13px">${r.tg_user_id}</td>
                            <td>${r.username ? `<a href="https://t.me/${r.username}" target="_blank" style="color:var(--primary);text-decoration:none">@${r.username}</a>` : '—'}</td>
                            <td>${r.first_name || '—'}</td>
                            <td><span class="badge ${statusCls}">${statusLabel[r.status] || r.status}</span></td>
                            <td style="font-size:12px;color:var(--text-muted);max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${r.error_message}">${r.error_message || '—'}</td>
                            <td style="color:var(--text-muted);font-size:12px">${r.sent_at ? timeAgo(r.sent_at) : '—'}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;

    // Bind buttons
    document.getElementById('btn-tg-fetch')?.addEventListener('click', async () => {
        showToast('Загрузка подписчиков...', 'info');
        try {
            const r = await api.post(`/api/telegram/campaigns/${campaignId}/fetch-members`, {});
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    // Master checkbox: select/deselect all
    const selectAllCb = document.getElementById('tg-select-all');
    const updateSelectedCount = () => {
        const all = document.querySelectorAll('.tg-rcpt-cb');
        const checked = document.querySelectorAll('.tg-rcpt-cb:checked');
        const countEl = document.getElementById('tg-selected-count');
        if (countEl && all.length > 0) countEl.textContent = `(выбрано ${checked.length} из ${all.length})`;
        if (selectAllCb) selectAllCb.checked = checked.length === all.length;
    };
    selectAllCb?.addEventListener('change', (e) => {
        document.querySelectorAll('.tg-rcpt-cb').forEach(cb => cb.checked = e.target.checked);
        updateSelectedCount();
    });
    document.querySelectorAll('.tg-rcpt-cb').forEach(cb => cb.addEventListener('change', updateSelectedCount));
    updateSelectedCount();

    document.getElementById('btn-tg-send')?.addEventListener('click', async () => {
        // Collect unchecked recipient IDs
        const unchecked = [...document.querySelectorAll('.tg-rcpt-cb:not(:checked)')].map(cb => parseInt(cb.dataset.id));
        const checked = document.querySelectorAll('.tg-rcpt-cb:checked').length;
        if (checked === 0) { showToast('Выберите хотя бы одного получателя', 'error'); return; }
        if (!confirm(`Запустить TG-рассылку для ${checked} получателей?`)) return;
        try {
            const r = await api.post(`/api/telegram/campaigns/${campaignId}/send`, { exclude_recipient_ids: unchecked });
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    document.getElementById('btn-tg-pause')?.addEventListener('click', async () => {
        try {
            const r = await api.post(`/api/telegram/campaigns/${campaignId}/pause`, {});
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    document.getElementById('btn-tg-cancel')?.addEventListener('click', async () => {
        if (!confirm('Отменить TG-рассылку?')) return;
        try {
            const r = await api.post(`/api/telegram/campaigns/${campaignId}/cancel`, {});
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    // Image upload
    document.getElementById('tg-image-input')?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) return showToast('Файл слишком большой (макс. 5 МБ)', 'error');
        showToast('Загрузка изображения...', 'info');
        try {
            const formData = new FormData();
            formData.append('file', file);
            const resp = await fetch(`/api/telegram/campaigns/${campaignId}/upload-image`, {
                method: 'POST',
                body: formData,
            });
            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || 'Upload failed');
            }
            const r = await resp.json();
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    // Image delete
    document.getElementById('btn-tg-del-image')?.addEventListener('click', async () => {
        try {
            const resp = await fetch(`/api/telegram/campaigns/${campaignId}/image`, { method: 'DELETE' });
            if (!resp.ok) throw new Error('Delete failed');
            const r = await resp.json();
            showToast(r.message, 'success');
            await renderTgCampaignDetail(container, campaignId);
        } catch (e) {
            showToast('Ошибка: ' + e.message, 'error');
        }
    });

    // Auto-refresh while sending
    if (c.status === 'sending') {
        setTimeout(async () => {
            const route = getRoute();
            if (route === `/telegram/${campaignId}`) {
                try { await renderTgCampaignDetail(container, campaignId); } catch {}
            }
        }, 5000);
    }
}

// Global actions for campaign list
window.tgSendCampaign = async function(id) {
    if (!confirm('Запустить TG-рассылку?')) return;
    try {
        const r = await api.post(`/api/telegram/campaigns/${id}/send`, {});
        showToast(r.message, 'success');
        handleRoute();
    } catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
};

window.tgPauseCampaign = async function(id) {
    try {
        const r = await api.post(`/api/telegram/campaigns/${id}/pause`, {});
        showToast(r.message, 'success');
        handleRoute();
    } catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
};

window.tgDeleteCampaign = async function(id) {
    if (!confirm('Удалить TG-кампанию?')) return;
    try {
        const r = await api.del(`/api/telegram/campaigns/${id}`);
        showToast(r.message, 'success');
        handleRoute();
    } catch (e) { showToast('Ошибка: ' + e.message, 'error'); }
};

// ══════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    handleRoute();
    updateSystemStatus();
    setInterval(updateSystemStatus, 15000);
});
window.addEventListener('hashchange', handleRoute);
