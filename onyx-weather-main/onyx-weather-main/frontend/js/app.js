/**
 * Main Application Dashboard Controller
 * Orchestrates multi-dimensional filtering, WebSocket real-time streams, Map & Feed updates.
 */

class WeatherApp {
  constructor() {
    this.map = null;
    this.charts = null;
    this.ws = null;
    this.reports = [];
    this.analytics = {};
    
    // Filter State
    this.filters = {
      preset_range: 'all',
      start_date: '',
      end_date: '',
      event_type: 'all',
      state: 'all',
      city: 'all',
      status: 'all',
      source: 'all',
      search: '',
      only_primaries: false
    };

    this.init();
  }

  async init() {
    // 1. Initialize Map & Charts
    this.map = new WeatherMap('india-map');
    this.charts = window.weatherAnalyticsCharts;
    if (this.charts) this.charts.initCharts();

    // 2. Setup Event Listeners
    this._bindEvents();

    // 3. Fetch Initial Data
    await this.fetchInitialState();

    // 4. Connect WebSocket for Real-Time Streaming Ingestion
    this._connectWebSocket();
  }

  async fetchInitialState() {
    try {
      await Promise.all([
        this.fetchAnalytics(),
        this.fetchReports(),
        this.fetchAlerts()
      ]);
    } catch (err) {
      console.error('Error fetching initial state:', err);
    }
  }

  async fetchAnalytics() {
    try {
      const [sumRes, timeRes] = await Promise.all([
        fetch('/api/analytics/summary'),
        fetch('/api/analytics/timeline')
      ]);
      const summary = await sumRes.json();
      const timeline = await timeRes.json();
      this.analytics = summary;

      // Update Metric Cards
      document.getElementById('stat-total-reports').innerText = summary.total_reports.toLocaleString();
      document.getElementById('stat-verified-reports').innerText = summary.total_verified.toLocaleString();
      document.getElementById('stat-fake-blocked').innerText = summary.total_fake_intercepted.toLocaleString();
      document.getElementById('stat-dedup-pct').innerText = summary.deduplication_reduction_pct + '%';
      document.getElementById('stat-active-alerts').innerText = summary.active_emergency_alerts;

      // Update Charts
      if (this.charts) {
        this.charts.updateData(summary, timeline);
      }
    } catch (e) {
      console.error('Analytics fetch error:', e);
    }
  }

  async fetchReports() {
    try {
      const params = new URLSearchParams();
      if (this.filters.preset_range && this.filters.preset_range !== 'all') params.append('preset_range', this.filters.preset_range);
      if (this.filters.start_date) params.append('start_date', this.filters.start_date);
      if (this.filters.end_date) params.append('end_date', this.filters.end_date);
      if (this.filters.event_type && this.filters.event_type !== 'all') params.append('event_type', this.filters.event_type);
      if (this.filters.state && this.filters.state !== 'all') params.append('state', this.filters.state);
      if (this.filters.city && this.filters.city !== 'all') params.append('city', this.filters.city);
      if (this.filters.status && this.filters.status !== 'all') params.append('status', this.filters.status);
      if (this.filters.source && this.filters.source !== 'all') params.append('source', this.filters.source);
      if (this.filters.search) params.append('search', this.filters.search);
      if (this.filters.only_primaries) params.append('only_primaries', 'true');
      params.append('limit', '250');

      const res = await fetch(`/api/reports?${params.toString()}`);
      const data = await res.json();
      this.reports = data.reports || [];

      // Update Map & Live Feed List
      if (this.map) this.map.updateMarkers(this.reports);
      this.renderFeed(this.reports);

      const countEl = document.getElementById('filter-result-count');
      if (countEl) countEl.innerText = `${this.reports.length} matching events`;
    } catch (e) {
      console.error('Reports fetch error:', e);
    }
  }

  async fetchAlerts() {
    try {
      const res = await fetch('/api/admin/alerts');
      const data = await res.json();
      const alerts = data.alerts || [];
      const tickerEl = document.getElementById('ticker-text');
      if (tickerEl && alerts.length > 0) {
        tickerEl.innerHTML = alerts.map(a => `<strong>[${a.severity.toUpperCase()} - ${a.state}]:</strong> ${a.title} &bull; ${a.instructions}`).join(' &nbsp;&nbsp;|&nbsp;&nbsp; ');
      }
    } catch (e) {
      console.error('Alerts fetch error:', e);
    }
  }

  renderFeed(reports) {
    const feedContainer = document.getElementById('live-feed-stream');
    if (!feedContainer) return;

    if (!reports || reports.length === 0) {
      feedContainer.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
          <span style="font-size: 2rem;">🔍</span>
          <p style="margin-top: 0.5rem;">No weather reports match your active filter criteria.</p>
        </div>
      `;
      return;
    }

    feedContainer.innerHTML = reports.map(r => {
      const isFake = r.verification_status === 'fake_misleading';
      const badgeClass = this._getBadgeClass(r.verification_status);
      const timeAgo = this._formatTime(r.timestamp);

      return `
        <div class="report-card ${isFake ? 'fake-flagged' : ''} fade-in" onclick="app.showDetailModal('${r.id}')">
          <div class="card-top">
            <div class="card-source-author">
              <span class="source-tag">${r.source}</span>
              <strong>${r.author_handle || '@Citizen'}</strong>
            </div>
            <span class="card-status-badge ${badgeClass}">${this._formatStatus(r.verification_status)}</span>
          </div>
          <p class="card-text">${this._escapeHtml(r.text)}</p>
          ${r.media_url ? `<img src="${r.media_url}" class="card-media" loading="lazy" alt="Media attachment">` : ''}
          <div class="card-meta">
            <span>📍 <strong>${r.city}</strong>, ${r.state}</span>
            <span>🕒 ${timeAgo}</span>
            ${r.cluster_size > 1 ? `<span class="card-cluster-info">🔗 ${r.cluster_size} Corroborated</span>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  showDetailModal(reportId) {
    const report = this.reports.find(r => r.id === reportId);
    if (!report) return;

    const modalBody = document.getElementById('modal-detail-content');
    if (!modalBody) return;

    const isFake = report.verification_status === 'fake_misleading';
    const hashtags = Array.isArray(report.hashtags) ? report.hashtags.join(' ') : report.hashtags;

    modalBody.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
        <div>
          <span class="source-tag">${report.source}</span>
          <h2 style="font-size: 1.25rem; font-weight: 700; margin-top: 0.35rem;">📍 ${report.city}, ${report.state}</h2>
          <span style="font-size: 0.8rem; color: var(--text-muted);">Timestamp: ${new Date(report.timestamp).toLocaleString()} &bull; ID: ${report.id}</span>
        </div>
        <span class="card-status-badge ${this._getBadgeClass(report.verification_status)}" style="font-size: 0.8rem; padding: 0.3rem 0.75rem;">
          ${this._formatStatus(report.verification_status)}
        </span>
      </div>

      <div style="background: var(--bg-tertiary); padding: 1rem; border-radius: var(--radius-sm); margin-bottom: 1rem; border-left: 3px solid var(--accent-cyan);">
        <p style="font-size: 0.95rem; line-height: 1.5;">"${this._escapeHtml(report.text)}"</p>
        <p style="margin-top: 0.5rem; color: var(--accent-cyan); font-size: 0.82rem;">${hashtags}</p>
      </div>

      ${report.media_url ? `
        <div style="margin-bottom: 1rem;">
          <img src="${report.media_url}" style="width: 100%; max-height: 240px; object-fit: cover; border-radius: 8px; border: 1px solid var(--border-glass);" alt="Media Preview">
        </div>
      ` : ''}

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem; font-size: 0.85rem;">
        <div style="background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px;">
          <span style="color: var(--text-secondary); display: block; font-size: 0.75rem;">EVENT CATEGORY</span>
          <strong>${(report.event_type || '').toUpperCase()} (${report.severity})</strong>
        </div>
        <div style="background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px;">
          <span style="color: var(--text-secondary); display: block; font-size: 0.75rem;">AI CONFIDENCE</span>
          <strong>${Math.round(report.ai_confidence * 100)}%</strong>
        </div>
        <div style="background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px;">
          <span style="color: var(--text-secondary); display: block; font-size: 0.75rem;">RADAR CROSS-VERIFICATION</span>
          <strong style="color: ${report.radar_cross_verified ? 'var(--accent-emerald)' : 'var(--accent-red)'}">
            ${report.radar_cross_verified ? '✓ Consistent with Radar Baseline' : '✗ Radar Discrepancy Detected'}
          </strong>
        </div>
        <div style="background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px;">
          <span style="color: var(--text-secondary); display: block; font-size: 0.75rem;">CLUSTER PRIMARY</span>
          <strong>${report.is_cluster_primary ? 'Primary Incident Source' : `Secondary (${report.cluster_size} items)`}</strong>
        </div>
      </div>

      ${report.admin_notes ? `
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.75rem; border-radius: 6px; font-size: 0.825rem; color: #fca5a5;">
          <strong>AI & Diagnostic Notes:</strong> ${report.admin_notes}
        </div>
      ` : ''}

      <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.75rem;">
        <button class="btn btn-secondary" onclick="app.closeDetailModal()">Close</button>
        <button class="btn btn-primary" onclick="app.flyToReport('${report.id}')">View on Map</button>
      </div>
    `;

    document.getElementById('modal-backdrop').classList.add('open');
  }

  closeDetailModal() {
    const el = document.getElementById('modal-backdrop');
    if (el) el.classList.remove('open');
  }

  flyToReport(reportId) {
    const report = this.reports.find(r => r.id === reportId);
    this.closeDetailModal();
    if (report && this.map) {
      this.map.flyToLocation(report.lat, report.lon, 12);
    }
  }

  _bindEvents() {
    // 1. Date Preset Pills
    document.querySelectorAll('.date-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        document.querySelectorAll('.date-pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        this.filters.preset_range = e.target.dataset.preset;
        this.fetchReports();
      });
    });

    // 2. Event Category Pills
    document.querySelectorAll('.event-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        document.querySelectorAll('.event-pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        this.filters.event_type = e.target.dataset.event;
        this.fetchReports();
      });
    });

    // 3. State & Status Dropdowns
    const stateSelect = document.getElementById('filter-state');
    if (stateSelect) {
      stateSelect.addEventListener('change', (e) => {
        this.filters.state = e.target.value;
        this.fetchReports();
      });
    }

    const statusSelect = document.getElementById('filter-status');
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        this.filters.status = e.target.value;
        this.fetchReports();
      });
    }

    const sourceSelect = document.getElementById('filter-source');
    if (sourceSelect) {
      sourceSelect.addEventListener('change', (e) => {
        this.filters.source = e.target.value;
        this.fetchReports();
      });
    }

    // 4. Search input with debounce
    const searchInput = document.getElementById('filter-search');
    if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.filters.search = e.target.value.trim();
          this.fetchReports();
        }, 300);
      });
    }

    // 5. Primaries only toggle
    const primaryToggle = document.getElementById('filter-primaries-only');
    if (primaryToggle) {
      primaryToggle.addEventListener('change', (e) => {
        this.filters.only_primaries = e.target.checked;
        this.fetchReports();
      });
    }

    // 6. Live Internet Data Sync Button
    const syncLiveBtn = document.getElementById('btn-sync-live');
    if (syncLiveBtn) {
      syncLiveBtn.addEventListener('click', async () => {
        syncLiveBtn.disabled = true;
        syncLiveBtn.innerText = '🌐 Ingesting Live Web Data...';
        
        let apiKeys = {};
        try {
          apiKeys = JSON.parse(localStorage.getItem('vayu_api_keys') || '{}');
        } catch(e) {}
        
        const token = localStorage.getItem('vayu_admin_token') || 'vdu-adm-imd-session-key-9982';
        
        try {
          const res = await fetch('/api/admin/sync-live-apis', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Admin-Token': token,
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(apiKeys)
          });
          const data = await res.json();
          if (data.success) {
            if (data.reports && data.reports.length > 0) {
              this.reports = [...data.reports, ...this.reports];
            }
            await this.fetchInitialState();
          }
        } catch (e) {
          console.error('Error syncing live web data:', e);
        } finally {
          syncLiveBtn.disabled = false;
          syncLiveBtn.innerText = '🌐 Live Internet Ingest';
        }
      });
    }

    // 7. Export Buttons
    const exportCsvBtn = document.getElementById('btn-export-csv');
    if (exportCsvBtn) {
      exportCsvBtn.addEventListener('click', () => {
        const params = new URLSearchParams();
        if (this.filters.event_type && this.filters.event_type !== 'all') params.append('event_type', this.filters.event_type);
        if (this.filters.state && this.filters.state !== 'all') params.append('state', this.filters.state);
        if (this.filters.status && this.filters.status !== 'all') params.append('status', this.filters.status);
        window.open(`/api/export/csv?${params.toString()}`, '_blank');
      });
    }

    const exportJsonBtn = document.getElementById('btn-export-json');
    if (exportJsonBtn) {
      exportJsonBtn.addEventListener('click', () => {
        const params = new URLSearchParams();
        if (this.filters.event_type && this.filters.event_type !== 'all') params.append('event_type', this.filters.event_type);
        if (this.filters.state && this.filters.state !== 'all') params.append('state', this.filters.state);
        if (this.filters.status && this.filters.status !== 'all') params.append('status', this.filters.status);
        window.open(`/api/export/json?${params.toString()}`, '_blank');
      });
    }
  }

  _connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/stream/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'NEW_REPORT' && msg.report) {
            this._handleIncomingStreamReport(msg.report);
          }
        } catch (e) {
          // pong or other non-json
        }
      };

      this.ws.onclose = () => {
        setTimeout(() => this._connectWebSocket(), 5000);
      };
    } catch (e) {
      console.warn('WebSocket connection fallback:', e);
    }
  }

  _handleIncomingStreamReport(newReport) {
    // Prepend to current reports list
    this.reports.unshift(newReport);
    if (this.reports.length > 300) this.reports.pop();

    // Update Map and Feed smoothly
    if (this.map) this.map.updateMarkers(this.reports);
    this.renderFeed(this.reports);

    // Increment counters dynamically
    const totalEl = document.getElementById('stat-total-reports');
    if (totalEl) {
      const current = parseInt(totalEl.innerText.replace(/,/g, '')) || 0;
      totalEl.innerText = (current + 1).toLocaleString();
    }

    // Refresh Analytics periodically
    this.fetchAnalytics();
  }

  _getBadgeClass(status) {
    switch (status) {
      case 'verified_imd': return 'badge-imd';
      case 'verified_ai': return 'badge-ai';
      case 'citizen_corroborated': return 'badge-citizen';
      case 'fake_misleading': return 'badge-fake';
      default: return 'badge-review';
    }
  }

  _formatStatus(status) {
    switch (status) {
      case 'verified_imd': return 'Official IMD';
      case 'verified_ai': return 'AI Verified';
      case 'citizen_corroborated': return 'Citizen Verified';
      case 'fake_misleading': return 'Fake / Hoax';
      default: return 'Under Review';
    }
  }

  _formatTime(isoStr) {
    try {
      const date = new Date(isoStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return 'Just now';
    }
  }

  _escapeHtml(str) {
    return (str || '').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new WeatherApp();
});
