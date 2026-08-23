/**
 * Admin Command Center & Moderation Controller
 */

class AdminPortal {
  constructor() {
    this.pendingReports = [];
    this.auditLogs = [];
    this.init();
  }

  async init() {
    await this.fetchModerationQueue();
    await this.fetchAuditLogs();
    this.bindEvents();
  }

  async fetchModerationQueue() {
    try {
      const res = await fetch('/api/reports?status=under_review,fake_misleading&limit=50');
      const data = await res.json();
      this.pendingReports = data.reports || [];
      this.renderQueue();
    } catch (e) {
      console.error('Error fetching queue:', e);
    }
  }

  async fetchAuditLogs() {
    try {
      const res = await fetch('/api/admin/moderation-logs?limit=25');
      const data = await res.json();
      this.auditLogs = data.logs || [];
      this.renderAuditLogs();
    } catch (e) {
      console.error('Error fetching audit logs:', e);
    }
  }

  renderQueue() {
    const container = document.getElementById('moderation-queue-list');
    if (!container) return;

    if (this.pendingReports.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
          <span style="font-size: 2.5rem;">🎉</span>
          <h3 style="margin-top: 0.5rem; color: var(--text-primary);">Moderation Queue is Clean!</h3>
          <p>No suspicious or unverified reports pending administrative review.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = this.pendingReports.map(r => {
      const isFake = r.verification_status === 'fake_misleading';
      const fakePct = Math.round((r.fake_probability || 0) * 100);

      return `
        <div class="glass-panel" style="padding: 1.25rem; margin-bottom: 1rem; border-left: 4px solid ${isFake ? 'var(--accent-red)' : 'var(--accent-amber)'};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div>
              <span class="source-tag">${r.source}</span>
              <strong style="margin-left: 0.5rem; font-size: 0.95rem;">${r.author_handle}</strong>
              <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.5rem;">📍 ${r.city}, ${r.state} &bull; 🕒 ${new Date(r.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <span style="font-size: 0.75rem; color: ${fakePct > 60 ? '#f87171' : '#fbbf24'}; font-weight: 700;">
                Fake Probability: ${fakePct}%
              </span>
              <span class="card-status-badge ${isFake ? 'badge-fake' : 'badge-review'}">
                ${isFake ? 'Flagged Fake' : 'Under Review'}
              </span>
            </div>
          </div>

          <p style="font-size: 0.9rem; margin-bottom: 0.75rem; line-height: 1.45; background: var(--bg-secondary); padding: 0.75rem; border-radius: 6px;">
            "${r.text}"
          </p>

          ${r.media_url ? `
            <div style="margin-bottom: 0.75rem;">
              <img src="${r.media_url}" style="height: 100px; border-radius: 6px; object-fit: cover;" alt="Report Media">
            </div>
          ` : ''}

          <div style="background: rgba(13, 21, 39, 0.6); padding: 0.65rem 0.85rem; border-radius: 6px; margin-bottom: 0.85rem; font-size: 0.8rem; border: 1px solid var(--border-glass);">
            <strong style="color: var(--accent-cyan);">AI Diagnostic Breakdown:</strong>
            <p style="color: var(--text-secondary); margin-top: 0.2rem;">${r.admin_notes || 'Automated NLP credibility evaluation pending.'}</p>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">Report ID: <code>${r.id}</code></div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-success" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'approve')">
                ✓ Verify & Publish
              </button>
              <button class="btn btn-danger" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'mark_fake')">
                ✗ Mark as Fake / Misinformation
              </button>
              <button class="btn btn-secondary" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'merge_cluster')">
                🔗 Merge Duplicate
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderAuditLogs() {
    const tbody = document.getElementById('audit-log-tbody');
    if (!tbody) return;

    tbody.innerHTML = this.auditLogs.map(l => `
      <tr>
        <td><code>${l.report_id}</code></td>
        <td><strong style="color: var(--accent-cyan);">${l.action.toUpperCase()}</strong></td>
        <td>${l.admin_user}</td>
        <td><span style="font-size: 0.75rem; color: var(--text-muted);">${l.previous_status} &rarr; ${l.new_status}</span></td>
        <td>${l.reason || 'Manual Action'}</td>
        <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
      </tr>
    `).join('');
  }

  async executeAction(reportId, action) {
    try {
      const res = await fetch('/api/admin/moderate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_id: reportId,
          action: action,
          admin_user: 'IMD_SuperAdmin',
          reason: `Action executed via Admin Command Workbench (${action})`
        })
      });
      const data = await res.json();
      if (data.success) {
        this.showToast(`Action "${action.toUpperCase()}" applied to report ${reportId}`);
        await this.fetchModerationQueue();
        await this.fetchAuditLogs();
      }
    } catch (e) {
      console.error('Moderation action failed:', e);
    }
  }

  async init() {
    await this.fetchModerationQueue();
    await this.fetchAuditLogs();
    await this.loadApiKeys();
    this.bindEvents();
  }

  async loadApiKeys() {
    try {
      const res = await fetch('/api/admin/api-keys');
      const data = await res.json();
      if (data && data.keys) {
        if (data.keys.OPENWEATHER_API_KEY && data.keys.OPENWEATHER_API_KEY !== 'Not Set') {
          document.getElementById('input-openweather-key').value = data.keys.OPENWEATHER_API_KEY;
          document.getElementById('text-openweather-status').innerText = 'Connected';
          document.getElementById('text-openweather-status').style.color = 'var(--accent-emerald)';
        }
        if (data.keys.NEWS_API_KEY && data.keys.NEWS_API_KEY !== 'Not Set') {
          document.getElementById('input-newsapi-key').value = data.keys.NEWS_API_KEY;
          document.getElementById('text-newsapi-status').innerText = 'Connected';
          document.getElementById('text-newsapi-status').style.color = 'var(--accent-emerald)';
        }
        if (data.keys.WEATHERAPI_KEY && data.keys.WEATHERAPI_KEY !== 'Not Set') {
          document.getElementById('input-weatherapi-key').value = data.keys.WEATHERAPI_KEY;
        }
        if (data.keys.GNEWS_API_KEY && data.keys.GNEWS_API_KEY !== 'Not Set') {
          document.getElementById('input-gnews-key').value = data.keys.GNEWS_API_KEY;
        }
      }
    } catch (e) {
      console.error('Error loading API keys:', e);
    }
  }

  async syncLiveApis() {
    const btn = document.getElementById('btn-sync-live-apis');
    if (btn) {
      btn.disabled = true;
      btn.innerText = '🌐 Fetching Live Internet Streams...';
    }

    try {
      const res = await fetch('/api/admin/sync-live-apis', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.showToast(`✓ Live Sync Complete! Ingested ${data.total_synced} real-time reports (${data.google_news_articles} live news + ${data.open_meteo_telemetry_stations} AWS stations).`);
        await this.fetchModerationQueue();
      }
    } catch (e) {
      console.error('Error syncing live APIs:', e);
      this.showToast('Error syncing live feeds.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = '🔄 Sync Live Internet Data Now';
      }
    }
  }

  bindEvents() {
    // Live API Sync Button
    const syncBtn = document.getElementById('btn-sync-live-apis');
    if (syncBtn) {
      syncBtn.addEventListener('click', () => this.syncLiveApis());
    }

    // API Keys Form
    const apiKeysForm = document.getElementById('form-api-keys');
    if (apiKeysForm) {
      apiKeysForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          OPENWEATHER_API_KEY: document.getElementById('input-openweather-key').value.trim(),
          NEWS_API_KEY: document.getElementById('input-newsapi-key').value.trim(),
          WEATHERAPI_KEY: document.getElementById('input-weatherapi-key').value.trim(),
          GNEWS_API_KEY: document.getElementById('input-gnews-key').value.trim()
        };
        try {
          const res = await fetch('/api/admin/api-keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.success) {
            this.showToast('💾 API Keys securely saved and active.');
            await this.loadApiKeys();
          }
        } catch (err) {
          console.error('Error saving API keys:', err);
        }
      });
    }

    // CAP Alert Broadcast Form
    const alertForm = document.getElementById('form-cap-alert');
    if (alertForm) {
      alertForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          title: document.getElementById('alert-title').value,
          event_type: document.getElementById('alert-event-type').value,
          severity: document.getElementById('alert-severity').value,
          state: document.getElementById('alert-state').value,
          districts: [document.getElementById('alert-district').value || 'All Coastal Districts'],
          instructions: document.getElementById('alert-instructions').value,
          valid_hours: parseInt(document.getElementById('alert-valid-hours').value) || 24
        };

        try {
          const res = await fetch('/api/admin/broadcast-alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.success) {
            this.showToast(`🚨 CAP Emergency Warning Broadcast Issued: ${data.alert_id}`);
            alertForm.reset();
          }
        } catch (err) {
          console.error('Error broadcasting alert:', err);
        }
      });
    }

    // Disaster Scenario Trigger Buttons
    document.querySelectorAll('.btn-scenario').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const scenario = e.currentTarget.dataset.scenario;
        try {
          const res = await fetch('/api/admin/trigger-scenario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario: scenario })
          });
          const data = await res.json();
          if (data.success) {
            this.showToast(`⚡ Scenario "${scenario}" triggered (${data.generated_reports_count} reports injected).`);
            await this.fetchModerationQueue();
          }
        } catch (err) {
          console.error('Scenario trigger error:', err);
        }
      });
    });
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>ℹ️</span> <span>${message}</span>`;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.adminPortal = new AdminPortal();
});
